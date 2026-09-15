from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import ai
from .ai import AIConfigError
from .clauses import split_clauses
from .demo import DEMO_LEASE, DEMO_LEASE_RENEWAL
from .diffing import compute_diff, classify_modified
from .extraction import extract_text, ExtractionError
from .models import (
    UploadResponse,
    SummaryResult,
    RiskResult,
    ChatRequest,
    ChatResponse,
    NextStepRequest,
    NextStepResult,
    CompareRequest,
    CompareResult,
    LawyerPrepRequest,
    LawyerPrepResult,
    DiffEntry,
)
from .storage import store

app = FastAPI(title="LegalLens API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the deployed frontend origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_doc(session_id: str, doc_id: str):
    doc = store.get_document(session_id, doc_id)
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found for this session. It may have expired or belongs to a different session.",
        )
    return doc


def _handle_ai_error(e: Exception):
    if isinstance(e, AIConfigError):
        raise HTTPException(status_code=503, detail=str(e))
    raise HTTPException(status_code=502, detail=f"AI request failed: {e}")


@app.get("/health")
def health():
    return {"status": "ok", "ai_configured": bool(ai.os.environ.get("GEMINI_API_KEY"))}


@app.post("/session")
def new_session():
    return {"session_id": store.new_session()}


@app.post("/documents/upload", response_model=UploadResponse)
async def upload_document(session_id: str, file: UploadFile = File(...)):
    content = await file.read()
    try:
        text = extract_text(file.filename, content)
    except ExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    clauses = split_clauses(text)
    session_id, doc_id = store.add_document(session_id, file.filename, text, clauses)
    return UploadResponse(
        session_id=session_id,
        doc_id=doc_id,
        name=file.filename,
        word_count=len(text.split()),
        clauses=clauses,
    )


@app.post("/documents/demo", response_model=UploadResponse)
def load_demo(session_id: str, variant: str = "lease"):
    text = DEMO_LEASE_RENEWAL if variant == "lease_renewal" else DEMO_LEASE
    name = "Sample Lease — Renewal Version.txt" if variant == "lease_renewal" else "Sample Residential Lease.txt"
    clauses = split_clauses(text)
    session_id, doc_id = store.add_document(session_id, name, text, clauses)
    return UploadResponse(
        session_id=session_id,
        doc_id=doc_id,
        name=name,
        word_count=len(text.split()),
        clauses=clauses,
    )


@app.get("/documents/{session_id}/{doc_id}/summary", response_model=SummaryResult)
def get_summary(session_id: str, doc_id: str):
    doc = _require_doc(session_id, doc_id)
    if doc.summary is None:
        try:
            doc.summary = ai.analyze_summary(doc.clauses)
        except Exception as e:
            _handle_ai_error(e)
    return doc.summary


@app.get("/documents/{session_id}/{doc_id}/risks", response_model=RiskResult)
def get_risks(session_id: str, doc_id: str):
    doc = _require_doc(session_id, doc_id)
    if doc.risks is None:
        try:
            doc.risks = ai.analyze_risks(doc.clauses)["risks"]
        except Exception as e:
            _handle_ai_error(e)
    return {"risks": doc.risks}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    doc = _require_doc(req.session_id, req.doc_id)
    retrieved = doc.index.retrieve(req.message, top_k=6)
    retrieved_clauses = [c for c, _score in retrieved]
    if not retrieved_clauses:
        # nothing in the document is even lexically related — still let the
        # model see a small fallback slice rather than an empty prompt
        retrieved_clauses = doc.clauses[:3]
    try:
        result = ai.answer_chat(retrieved_clauses, req.history, req.message)
    except Exception as e:
        _handle_ai_error(e)
    result["retrievedClauses"] = [c.id for c in retrieved_clauses]
    return result


@app.post("/next-steps", response_model=NextStepResult)
def get_next_steps(req: NextStepRequest):
    doc = _require_doc(req.session_id, req.doc_id)
    if req.question:
        retrieved = [c for c, _s in doc.index.retrieve(req.question, top_k=6)]
    else:
        retrieved = doc.clauses[:12]
    if not retrieved:
        retrieved = doc.clauses[:6]
    try:
        return ai.next_steps(retrieved, req.question)
    except Exception as e:
        _handle_ai_error(e)


@app.post("/compare", response_model=CompareResult)
def compare(req: CompareRequest):
    doc_a = _require_doc(req.session_id, req.doc_id_a)
    doc_b = _require_doc(req.session_id, req.doc_id_b)

    computed = compute_diff(doc_a.clauses, doc_b.clauses)
    meaningful = [e for e in computed if e.kind in ("added", "removed", "modified")]

    try:
        described = ai.describe_diff(meaningful, doc_a.clauses, doc_b.clauses)
    except Exception as e:
        _handle_ai_error(e)

    return CompareResult(
        computedDiff=computed,
        added=described.get("added", []),
        removed=described.get("removed", []),
        changedWording=described.get("changedWording", []),
        changedAmounts=described.get("changedAmounts", []),
        changedDates=described.get("changedDates", []),
        changedObligations=described.get("changedObligations", []),
        changedTermination=described.get("changedTermination", []),
    )


@app.post("/lawyer-prep", response_model=LawyerPrepResult)
def get_lawyer_prep(req: LawyerPrepRequest):
    doc = _require_doc(req.session_id, req.doc_id)
    try:
        result = ai.lawyer_prep(doc.clauses, req.concern)
    except Exception as e:
        _handle_ai_error(e)
    doc.lawyer_prep = result
    return result
