"""Pydantic request/response models for the LegalLens API."""
from typing import List, Optional
from pydantic import BaseModel, Field


class Clause(BaseModel):
    id: str
    heading: str
    text: str


class DocumentMeta(BaseModel):
    session_id: str
    doc_id: str
    name: str
    word_count: int
    clause_count: int


class UploadResponse(BaseModel):
    session_id: str
    doc_id: str
    name: str
    word_count: int
    clauses: List[Clause]


class ImportantDate(BaseModel):
    label: str
    detail: str
    clauseId: Optional[str] = None


class SummaryResult(BaseModel):
    documentType: str
    summary: str
    obligations: List[str] = []
    rights: List[str] = []
    payments: List[str] = []
    importantDates: List[ImportantDate] = []
    restrictions: List[str] = []
    terminationConditions: List[str] = []
    consequences: List[str] = []
    missingOrInconsistent: List[str] = []


class RiskItem(BaseModel):
    clauseId: Optional[str] = None
    title: str
    category: str
    severity: str  # high | medium | standard
    explanation: str


class RiskResult(BaseModel):
    risks: List[RiskItem] = []


class ChatRequest(BaseModel):
    session_id: str
    doc_id: str
    message: str
    history: List[dict] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    citedClauses: List[str] = []
    documentSupport: str = "full"  # full | partial | none
    retrievedClauses: List[str] = []  # clause ids retrieval actually surfaced


class NextStepRequest(BaseModel):
    session_id: str
    doc_id: str
    question: Optional[str] = None


class NextStepResult(BaseModel):
    steps: List[str] = []
    rationale: Optional[str] = None


class CompareRequest(BaseModel):
    session_id: str
    doc_id_a: str
    doc_id_b: str


class DiffEntry(BaseModel):
    kind: str  # added | removed | modified | unchanged
    clause_id_a: Optional[str] = None
    clause_id_b: Optional[str] = None
    similarity: Optional[float] = None
    text_a: Optional[str] = None
    text_b: Optional[str] = None


class CompareResult(BaseModel):
    computedDiff: List[DiffEntry]
    added: List[str] = []
    removed: List[str] = []
    changedWording: List[str] = []
    changedAmounts: List[str] = []
    changedDates: List[str] = []
    changedObligations: List[str] = []
    changedTermination: List[str] = []


class LawyerPrepRequest(BaseModel):
    session_id: str
    doc_id: str
    concern: Optional[str] = None


class KeyClause(BaseModel):
    clauseId: str
    title: str


class LawyerPrepResult(BaseModel):
    documentType: str
    keyClauses: List[KeyClause] = []
    importantDates: List[ImportantDate] = []
    potentialIssues: List[str] = []
    questions: List[str] = []
