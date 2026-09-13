"""Computed (non-AI) clause-level diff between two versions of a document.

Clauses are aligned using difflib's SequenceMatcher over clause text
similarity ratios, not by trusting an LLM to describe the difference —
so "added", "removed", and "modified" are facts derived from the text
itself. The LLM is only used afterwards, on top of this computed diff, to
phrase the human-readable explanation (see ai.py:describe_diff).
"""
import re
from difflib import SequenceMatcher
from typing import List
from .models import Clause, DiffEntry

MODIFIED_THRESHOLD = 0.55  # below this ratio, treat as unrelated (add+remove) rather than modified
AMOUNT_RE = re.compile(r"\$\s?[\d,]+(?:\.\d+)?|\b\d+(?:\.\d+)?\s?%")
DATE_PERIOD_RE = re.compile(
    r"\b\d+\s?(?:day|days|month|months|year|years)\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b", re.I
)


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def compute_diff(clauses_a: List[Clause], clauses_b: List[Clause]) -> List[DiffEntry]:
    """Greedy best-match alignment: for each clause in A, find its closest
    unclaimed clause in B by text similarity. Anything left unclaimed in B
    is 'added'; anything in A with no good match is 'removed'."""
    used_b = set()
    entries: List[DiffEntry] = []

    for ca in clauses_a:
        best_b, best_score = None, 0.0
        for cb in clauses_b:
            if cb.id in used_b:
                continue
            score = _ratio(ca.text, cb.text)
            if score > best_score:
                best_b, best_score = cb, score

        if best_b is not None and best_score >= MODIFIED_THRESHOLD:
            used_b.add(best_b.id)
            # Only byte-identical text counts as unchanged — any textual
            # difference at all, however small, is a "modified" clause,
            # since a single changed number (a fee, a day count) is exactly
            # the kind of change this scanner exists to catch.
            kind = "unchanged" if ca.text.strip() == best_b.text.strip() else "modified"
            entries.append(
                DiffEntry(
                    kind=kind,
                    clause_id_a=ca.id,
                    clause_id_b=best_b.id,
                    similarity=round(best_score, 3),
                    text_a=ca.text,
                    text_b=best_b.text,
                )
            )
        else:
            entries.append(
                DiffEntry(kind="removed", clause_id_a=ca.id, text_a=ca.text, similarity=0.0)
            )

    for cb in clauses_b:
        if cb.id not in used_b:
            entries.append(
                DiffEntry(kind="added", clause_id_b=cb.id, text_b=cb.text, similarity=0.0)
            )

    return entries


def classify_modified(entry: DiffEntry) -> List[str]:
    """For a 'modified' entry, cheaply flag *what kind* of change it looks
    like (amount vs date/period vs pure wording) by diffing the numeric
    tokens directly — computed, not inferred by the LLM."""
    tags = []
    amounts_a, amounts_b = set(AMOUNT_RE.findall(entry.text_a or "")), set(
        AMOUNT_RE.findall(entry.text_b or "")
    )
    if amounts_a != amounts_b:
        tags.append("amount")
    dates_a, dates_b = set(DATE_PERIOD_RE.findall(entry.text_a or "")), set(
        DATE_PERIOD_RE.findall(entry.text_b or "")
    )
    if dates_a != dates_b:
        tags.append("date_or_period")
    if not tags:
        tags.append("wording")
    return tags
