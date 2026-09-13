"""Split a document's raw text into clause-level chunks with stable IDs.

This is the chunking stage of the retrieval pipeline: metadata (clause id,
heading, position) is preserved on every chunk so later stages (vector
retrieval, LLM prompts, UI citations) can always trace an answer back to a
specific piece of source text.
"""
import re
from typing import List
from .models import Clause

NUMBERED_CLAUSE_RE = re.compile(
    r"\n(?=\s*(?:\d{1,2}(?:\.\d{1,2})?\.\s+[A-Z]|Section\s+\d+|Article\s+\d+|SECTION\s+\d+|ARTICLE\s+\d+))"
)


def split_clauses(text: str, max_clauses: int = 80) -> List[Clause]:
    normalized = text.replace("\r\n", "\n").strip()

    parts = [p.strip() for p in NUMBERED_CLAUSE_RE.split(normalized) if p.strip()]
    if len(parts) < 3:
        # Fall back to paragraph-level chunking for documents without
        # numbered clauses (e.g. prose policies, letters).
        parts = [p.strip() for p in re.split(r"\n\s*\n", normalized) if len(p.strip()) > 25]
    if not parts:
        parts = [normalized] if normalized else []

    parts = parts[:max_clauses]
    clauses = []
    for i, p in enumerate(parts):
        heading = p.split("\n")[0].strip()[:80]
        clauses.append(Clause(id=f"C{i+1}", heading=heading, text=p))
    return clauses
