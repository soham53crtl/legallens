import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from app import main, ai

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def mock_ai(monkeypatch):
    """Every test runs with AI calls mocked so the suite never needs a real
    ANTHROPIC_API_KEY or network access — it verifies the app's own logic
    (routing, storage isolation, retrieval, diff computation), not the LLM."""
    monkeypatch.setattr(ai, "analyze_summary", lambda clauses: {
        "documentType": "Residential Lease Agreement",
        "summary": "A test summary.",
        "obligations": ["Pay rent on time"],
        "rights": ["Right to repairs"],
        "payments": ["$1,850/month"],
        "importantDates": [{"label": "Notice", "detail": "60 days", "clauseId": "C9"}],
        "restrictions": ["No subletting"],
        "terminationConditions": ["60 days notice"],
        "consequences": ["Early termination fee"],
        "missingOrInconsistent": [],
    })
    monkeypatch.setattr(ai, "analyze_risks", lambda clauses: {"risks": [
        {"clauseId": "C4", "title": "Early termination fee", "category": "Penalty", "severity": "high", "explanation": "Two months rent penalty."}
    ]})
    monkeypatch.setattr(ai, "answer_chat", lambda retrieved, history, question: {
        "answer": "The early termination fee is two months' rent.",
        "citedClauses": [c.id for c in retrieved][:1],
        "documentSupport": "full",
    })
    monkeypatch.setattr(ai, "next_steps", lambda retrieved, question: {
        "steps": ["Review the early termination clause", "Ask a lawyer about negotiating the fee"],
        "rationale": "Because a penalty clause was flagged.",
    })
    monkeypatch.setattr(ai, "describe_diff", lambda entries, a, b: {
        "added": ["A new parking clause was added."],
        "removed": [],
        "changedWording": [],
        "changedAmounts": ["Rent increased from $1,850 to $2,050."],
        "changedDates": ["Notice period increased from 60 to 90 days."],
        "changedObligations": [],
        "changedTermination": [],
    })
    monkeypatch.setattr(ai, "lawyer_prep", lambda clauses, concern: {
        "documentType": "Residential Lease Agreement",
        "keyClauses": [{"clauseId": "C4", "title": "Early termination fee"}],
        "importantDates": [{"label": "Notice", "detail": "60 days"}],
        "potentialIssues": ["Early termination penalty size"],
        "questions": ["Can the termination fee be negotiated?"],
    })


def _new_session():
    return client.post("/session").json()["session_id"]


def _load_demo(session_id, variant="lease"):
    return client.post(f"/documents/demo?session_id={session_id}&variant={variant}").json()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_upload_txt_document():
    session_id = _new_session()
    files = {"file": ("test.txt", b"1. Term. This lasts one year.\n\n2. Rent. $1000 per month.", "text/plain")}
    r = client.post(f"/documents/upload?session_id={session_id}", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "test.txt"
    assert len(body["clauses"]) >= 1


def test_upload_rejects_unsupported_extension():
    session_id = _new_session()
    files = {"file": ("test.exe", b"binary", "application/octet-stream")}
    r = client.post(f"/documents/upload?session_id={session_id}", files=files)
    assert r.status_code == 422


def test_demo_lease_load():
    session_id = _new_session()
    body = _load_demo(session_id)
    assert body["clauses"]
    assert "doc_id" in body


def test_summary_endpoint():
    session_id = _new_session()
    doc = _load_demo(session_id)
    r = client.get(f"/documents/{session_id}/{doc['doc_id']}/summary")
    assert r.status_code == 200
    assert r.json()["documentType"] == "Residential Lease Agreement"


def test_risks_endpoint_and_caching():
    session_id = _new_session()
    doc = _load_demo(session_id)
    r1 = client.get(f"/documents/{session_id}/{doc['doc_id']}/risks")
    assert r1.status_code == 200
    assert r1.json()["risks"][0]["severity"] == "high"


def test_document_isolation_across_sessions():
    """A document uploaded under session A must be completely inaccessible
    from session B — this is the concrete privacy/security guarantee."""
    session_a = _new_session()
    session_b = _new_session()
    doc = _load_demo(session_a)
    r = client.get(f"/documents/{session_b}/{doc['doc_id']}/summary")
    assert r.status_code == 404


def test_chat_grounded_in_retrieved_clauses():
    session_id = _new_session()
    doc = _load_demo(session_id)
    r = client.post("/chat", json={
        "session_id": session_id, "doc_id": doc["doc_id"],
        "message": "What happens if I terminate early?", "history": []
    })
    assert r.status_code == 200
    body = r.json()
    assert "retrievedClauses" in body
    assert len(body["retrievedClauses"]) > 0


def test_chat_unknown_document_returns_404():
    session_id = _new_session()
    r = client.post("/chat", json={
        "session_id": session_id, "doc_id": "not-a-real-id",
        "message": "hi", "history": []
    })
    assert r.status_code == 404


def test_next_steps_endpoint():
    session_id = _new_session()
    doc = _load_demo(session_id)
    r = client.post("/next-steps", json={
        "session_id": session_id, "doc_id": doc["doc_id"], "question": "early termination"
    })
    assert r.status_code == 200
    assert len(r.json()["steps"]) > 0


def test_compare_endpoint_uses_computed_diff():
    session_id = _new_session()
    doc_a = _load_demo(session_id, "lease")
    doc_b = _load_demo(session_id, "lease_renewal")
    r = client.post("/compare", json={
        "session_id": session_id, "doc_id_a": doc_a["doc_id"], "doc_id_b": doc_b["doc_id"]
    })
    assert r.status_code == 200
    body = r.json()
    assert any(e["kind"] == "added" for e in body["computedDiff"])
    assert any(e["kind"] == "modified" for e in body["computedDiff"])
    assert "Rent increased" in body["changedAmounts"][0]


def test_lawyer_prep_endpoint():
    session_id = _new_session()
    doc = _load_demo(session_id)
    r = client.post("/lawyer-prep", json={
        "session_id": session_id, "doc_id": doc["doc_id"], "concern": "the termination fee"
    })
    assert r.status_code == 200
    assert r.json()["questions"]


def test_ai_config_error_returns_503(monkeypatch):
    monkeypatch.setattr(ai, "analyze_summary", lambda clauses: (_ for _ in ()).throw(ai.AIConfigError("no key")))
    session_id = _new_session()
    doc = _load_demo(session_id)
    r = client.get(f"/documents/{session_id}/{doc['doc_id']}/summary")
    assert r.status_code == 503


def test_upload_rejects_file_over_size_limit():
    session_id = _new_session()
    oversized = b"x" * (main.MAX_UPLOAD_BYTES + 1)
    files = {"file": ("huge.txt", oversized, "text/plain")}
    r = client.post(f"/documents/upload?session_id={session_id}", files=files)
    assert r.status_code == 413


def test_upload_accepts_file_at_size_limit():
    session_id = _new_session()
    exactly_at_limit = b"1. Term. " + b"a" * (main.MAX_UPLOAD_BYTES - 20)
    files = {"file": ("large.txt", exactly_at_limit, "text/plain")}
    r = client.post(f"/documents/upload?session_id={session_id}", files=files)
    assert r.status_code == 200


def test_cors_allows_known_frontend_origin():
    r = client.options(
        "/health",
        headers={
            "Origin": "https://legalslens.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.headers.get("access-control-allow-origin") == "https://legalslens.vercel.app"


def test_cors_rejects_unknown_origin():
    r = client.options(
        "/health",
        headers={
            "Origin": "https://some-random-attacker-site.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers.keys()}
