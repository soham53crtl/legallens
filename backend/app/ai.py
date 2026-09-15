"""All LLM calls funnel through here.

Requires GEMINI_API_KEY to be set in the environment (get one free, no
card required, at https://aistudio.google.com/apikey). In production
(e.g. Render) this comes from the platform's secret store - it is never
sent from or exposed to the frontend. If the key is missing, every
function here raises AIConfigError with a clear message rather than
failing silently.
"""
import json
import os
from typing import List, Optional
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_BASE = """You are the analysis engine behind LegalLens, an AI legal-information and document-assistance tool. You are NOT a lawyer and never provide legal advice.
Rules you must always follow:
1. Use ONLY information present in the clause text provided to you. Never invent clauses, laws, statistics, or facts.
2. Never make definitive predictions about legal outcomes (e.g. never say something like "you will win" or "this is illegal"). Describe what the document says and general informational context only.
3. If information needed to answer is missing, incomplete, or ambiguous, say so explicitly rather than guessing.
4. Reference clause IDs (e.g. "C4") from the list you are given wherever a claim can be traced to a specific clause.
5. Keep fields concise. Respond with ONLY valid JSON matching the schema given - no markdown fences, no commentary, no text outside the JSON object."""


class AIConfigError(Exception):
    pass


def _client() -> genai.Client:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise AIConfigError(
            "GEMINI_API_KEY is not set. Set it in the backend environment to enable AI features "
            "(free key: https://aistudio.google.com/apikey)."
        )
    return genai.Client(api_key=key)


def _clause_block(clauses) -> str:
    return "\n".join(f"{c.id}: {c.text[:320].strip()}" for c in clauses)


def _call_json(system: str, user: str) -> dict:
    client = _client()
    config = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=2000,
        response_mime_type="application/json",
    )
    try:
        resp = client.models.generate_content(model=MODEL, contents=user, config=config)
    except genai_errors.APIError as e:
        raise AIConfigError(f"Gemini API error: {e}")
    raw = (resp.text or "").strip()
    return _parse_json(raw, system, user, client, config)


def _parse_json(raw: str, system: str, user: str, client: genai.Client, config) -> dict:
    cleaned = raw.strip()
    for fence in ("```json", "```"):
        if cleaned.startswith(fence):
            cleaned = cleaned[len(fence):]
    if cleaned.endswith("```"):
        cleaned = cleaned[: -3]
    cleaned = cleaned.strip()
    first, last = cleaned.find("{"), cleaned.rfind("}")
    if first >= 0 and last > first:
        cleaned = cleaned[first : last + 1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        stricter_config = types.GenerateContentConfig(
            system_instruction=system + "\nCRITICAL: return ONLY the JSON object, nothing else.",
            max_output_tokens=config.max_output_tokens,
            response_mime_type="application/json",
        )
        resp = client.models.generate_content(model=MODEL, contents=user, config=stricter_config)
        raw2 = (resp.text or "").strip()
        first, last = raw2.find("{"), raw2.rfind("}")
        return json.loads(raw2[first : last + 1])


def analyze_summary(clauses) -> dict:
    prompt = f"""Analyze this legal document, split into numbered clauses. Return ONLY a JSON object:
{{
 "documentType": "short label e.g. Residential Lease Agreement",
 "summary": "2-4 sentence plain-language summary",
 "obligations": ["up to 6 short phrases"],
 "rights": ["up to 5 short phrases"],
 "payments": ["up to 5 short phrases, with amounts if stated"],
 "importantDates": [{{"label":"short label","detail":"what happens / by when","clauseId":"C_"}}],
 "restrictions": ["up to 5 short phrases"],
 "terminationConditions": ["up to 5 short phrases"],
 "consequences": ["up to 5 short phrases"],
 "missingOrInconsistent": ["up to 3 notes, empty array if none"]
}}

CLAUSES:
{_clause_block(clauses)}"""
    return _call_json(SYSTEM_BASE, prompt)


def analyze_risks(clauses) -> dict:
    prompt = f"""Review these clauses for a non-lawyer reader. Identify concerning clauses, financial obligations, penalties, termination conditions, notice periods, renewal/auto-renewal clauses, confidentiality obligations, non-compete/non-solicitation, dispute-resolution clauses (arbitration, jury trial waivers), and missing/inconsistent information.
Return ONLY a JSON object:
{{ "risks": [
  {{"clauseId":"C_","title":"short title","category":"Financial Obligation|Penalty|Termination|Notice Period|Renewal|Confidentiality|Non-Compete|Dispute Resolution|Missing/Inconsistent|Other","severity":"high|medium|standard","explanation":"one plain-language sentence"}}
] }}
At most 10 items, high severity first.

CLAUSES:
{_clause_block(clauses)}"""
    return _call_json(SYSTEM_BASE, prompt)


def answer_chat(retrieved_clauses, history: List[dict], question: str) -> dict:
    history_text = "\n".join(f"{h['role']}: {h['text']}" for h in history[-6:])
    prompt = f"""Conversation so far:
{history_text}

New question: {question}

The clauses below were retrieved by the document's search index as the most relevant to this question - they are NOT necessarily the whole document. Answer using only these clauses.
Return ONLY a JSON object:
{{"answer":"1-4 sentence plain-language answer","citedClauses":["ids that support the answer"],"documentSupport":"full|partial|none"}}
If these clauses don't actually address the question, set documentSupport to "none" and say so plainly rather than fabricating an answer.

RETRIEVED CLAUSES:
{_clause_block(retrieved_clauses)}"""
    return _call_json(SYSTEM_BASE, prompt)


def next_steps(retrieved_clauses, question: Optional[str]) -> dict:
    context = f'The user asked: "{question}"' if question else "The user wants general next steps for handling this document."
    prompt = f"""{context}
Based only on the clauses below, suggest general informational next steps - never definitive legal advice, never a predicted outcome.
Return ONLY a JSON object:
{{"steps": ["up to 4 short, concrete next steps, e.g. 'Review Clause 7', 'Collect proof of payment history', 'Ask a lawyer about the early-termination fee'"], "rationale": "one sentence on why these steps, or null"}}

CLAUSES:
{_clause_block(retrieved_clauses)}"""
    return _call_json(SYSTEM_BASE, prompt)


def describe_diff(diff_entries, clauses_a, clauses_b) -> dict:
    """Takes the *computed* diff (from diffing.py) and asks the LLM only to
    phrase it for a non-lawyer reader - it cannot invent a difference that
    the computed diff didn't already find, since only the flagged entries
    are passed in."""
    lines = []
    for e in diff_entries:
        if e.kind == "added":
            lines.append(f"ADDED (B:{e.clause_id_b}): {e.text_b[:300]}")
        elif e.kind == "removed":
            lines.append(f"REMOVED (A:{e.clause_id_a}): {e.text_a[:300]}")
        elif e.kind == "modified":
            lines.append(
                f"MODIFIED (A:{e.clause_id_a} -> B:{e.clause_id_b}, similarity={e.similarity}):\n  OLD: {e.text_a[:300]}\n  NEW: {e.text_b[:300]}"
            )
    prompt = f"""Below is a pre-computed, verified list of clause-level differences between Document A and Document B (already determined by text comparison - do not add or remove any differences, only explain the ones listed).
For each MODIFIED entry, classify it into one or more of: changedWording, changedAmounts, changedDates, changedObligations, changedTermination.
Return ONLY a JSON object:
{{ "added": ["short description per ADDED entry"],
  "removed": ["short description per REMOVED entry"],
  "changedWording": ["short old-vs-new description"],
  "changedAmounts": ["short old-vs-new description"],
  "changedDates": ["short old-vs-new description"],
  "changedObligations": ["short old-vs-new description"],
  "changedTermination": ["short old-vs-new description"] }}

COMPUTED DIFF:
{chr(10).join(lines) if lines else "(no differences detected)"}"""
    return _call_json(SYSTEM_BASE, prompt)


def lawyer_prep(clauses, concern: Optional[str]) -> dict:
    concern_line = f'The user\'s stated concern: "{concern}"' if concern else "No specific concern stated - general review requested."
    prompt = f"""Create a lawyer-preparation briefing for this document. {concern_line}
Return ONLY a JSON object:
{{ "documentType":"short label",
  "keyClauses":[{{"clauseId":"C_","title":"short title"}}],
  "importantDates":[{{"label":"...","detail":"..."}}],
  "potentialIssues":["up to 5 short descriptions"],
  "questions":["up to 6 specific questions to ask a legal professional"] }}

CLAUSES:
{_clause_block(clauses)}"""
    return _call_json(SYSTEM_BASE, prompt)
