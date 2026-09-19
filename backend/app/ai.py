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
import time
from typing import List, Optional
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
import openai

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_MAX_OUTPUT_TOKENS = 4096

# Gemini's free tier occasionally returns 503 UNAVAILABLE / "high demand" -
# a transient overload on Google's side, not an error in our request. Retry
# a few times with backoff before surfacing anything to the user.
TRANSIENT_RETRY_ATTEMPTS = 3
TRANSIENT_RETRY_BASE_DELAY_SECONDS = 2

# Grok (xAI) fallback: only used if Gemini fails outright (after its own
# retries above) AND an XAI_API_KEY is configured. Gemini stays the primary
# path in every case - this never changes behavior when Gemini succeeds.
GROK_MODEL = os.environ.get("GROK_MODEL", "grok-4-fast")
GROK_BASE_URL = "https://api.x.ai/v1"

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


# ---------------------------------------------------------------------------
# JSON schemas
#
# These are passed as response_schema so Gemini uses constrained decoding to
# guarantee structurally valid, on-shape JSON, instead of just being asked
# nicely in the prompt. This is what actually prevents "Expecting ','
# delimiter" / truncated-JSON errors - the mime type alone does not.
# ---------------------------------------------------------------------------

_STR = {"type": "STRING"}
_STR_ARRAY = {"type": "ARRAY", "items": _STR}

SUMMARY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "documentType": _STR,
        "summary": _STR,
        "obligations": _STR_ARRAY,
        "rights": _STR_ARRAY,
        "payments": _STR_ARRAY,
        "importantDates": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"label": _STR, "detail": _STR, "clauseId": _STR},
                "required": ["label", "detail"],
            },
        },
        "restrictions": _STR_ARRAY,
        "terminationConditions": _STR_ARRAY,
        "consequences": _STR_ARRAY,
        "missingOrInconsistent": _STR_ARRAY,
    },
    "required": [
        "documentType", "summary", "obligations", "rights", "payments",
        "importantDates", "restrictions", "terminationConditions",
        "consequences", "missingOrInconsistent",
    ],
}

RISKS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "risks": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "clauseId": _STR,
                    "title": _STR,
                    "category": {
                        "type": "STRING",
                        "enum": [
                            "Financial Obligation", "Penalty", "Termination",
                            "Notice Period", "Renewal", "Confidentiality",
                            "Non-Compete", "Dispute Resolution",
                            "Missing/Inconsistent", "Other",
                        ],
                    },
                    "severity": {"type": "STRING", "enum": ["high", "medium", "standard"]},
                    "explanation": _STR,
                },
                "required": ["clauseId", "title", "category", "severity", "explanation"],
            },
        }
    },
    "required": ["risks"],
}

CHAT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "answer": _STR,
        "citedClauses": _STR_ARRAY,
        "documentSupport": {"type": "STRING", "enum": ["full", "partial", "none"]},
    },
    "required": ["answer", "citedClauses", "documentSupport"],
}

NEXT_STEPS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "steps": _STR_ARRAY,
        "rationale": {"type": "STRING", "nullable": True},
    },
    "required": ["steps"],
}

DIFF_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "added": _STR_ARRAY,
        "removed": _STR_ARRAY,
        "changedWording": _STR_ARRAY,
        "changedAmounts": _STR_ARRAY,
        "changedDates": _STR_ARRAY,
        "changedObligations": _STR_ARRAY,
        "changedTermination": _STR_ARRAY,
    },
    "required": [
        "added", "removed", "changedWording", "changedAmounts",
        "changedDates", "changedObligations", "changedTermination",
    ],
}

LAWYER_PREP_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "documentType": _STR,
        "keyClauses": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"clauseId": _STR, "title": _STR},
                "required": ["clauseId", "title"],
            },
        },
        "importantDates": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"label": _STR, "detail": _STR},
                "required": ["label", "detail"],
            },
        },
        "potentialIssues": _STR_ARRAY,
        "questions": _STR_ARRAY,
    },
    "required": ["documentType", "keyClauses", "importantDates", "potentialIssues", "questions"],
}


# ---------------------------------------------------------------------------
# Core call/parse machinery
# ---------------------------------------------------------------------------

def _finish_reason(resp):
    try:
        return resp.candidates[0].finish_reason
    except Exception:
        return None


def _was_truncated(resp) -> bool:
    reason = _finish_reason(resp)
    return reason is not None and "MAX_TOKEN" in str(reason)


def _extract_json_object(text: str) -> str:
    cleaned = (text or "").strip()
    for fence in ("```json", "```"):
        if cleaned.startswith(fence):
            cleaned = cleaned[len(fence):]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    first, last = cleaned.find("{"), cleaned.rfind("}")
    if first >= 0 and last > first:
        cleaned = cleaned[first : last + 1]
    return cleaned


def _is_transient(e: genai_errors.APIError) -> bool:
    code = getattr(e, "code", None)
    return code in (503, 429)


def _generate(client, system: str, user: str, schema: dict, max_output_tokens: int):
    config = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_output_tokens,
        response_mime_type="application/json",
        response_schema=schema,
    )
    last_error = None
    for attempt in range(1, TRANSIENT_RETRY_ATTEMPTS + 1):
        try:
            return client.models.generate_content(model=MODEL, contents=user, config=config)
        except genai_errors.APIError as e:
            last_error = e
            if _is_transient(e) and attempt < TRANSIENT_RETRY_ATTEMPTS:
                # Exponential backoff: 2s, 4s, ... before trying again.
                time.sleep(TRANSIENT_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)))
                continue
            raise AIConfigError(f"Gemini API error: {e}")
    # Unreachable, but keeps type-checkers happy.
    raise AIConfigError(f"Gemini API error: {last_error}")


def _call_json_gemini(system: str, user: str, schema: dict, max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS) -> dict:
    client = _client()
    resp = _generate(client, system, user, schema, max_output_tokens)
    raw = (resp.text or "").strip()
    cleaned = _extract_json_object(raw)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass  # fall through to retry below

    # First attempt failed to parse. Two distinct causes need two distinct
    # fixes: the response got cut off (finish_reason == MAX_TOKENS), in
    # which case re-asking with the same budget will just fail again the
    # same way - so double the budget. Otherwise it's the model wrapping or
    # garbling the JSON, so just remind it more sternly.
    if _was_truncated(resp):
        retry_system = system
        retry_tokens = max_output_tokens * 2
    else:
        retry_system = system + "\nCRITICAL: return ONLY the JSON object, nothing else. Make sure it is complete and valid JSON."
        retry_tokens = max_output_tokens

    resp2 = _generate(client, retry_system, user, schema, retry_tokens)
    raw2 = (resp2.text or "").strip()
    cleaned2 = _extract_json_object(raw2)
    try:
        return json.loads(cleaned2)
    except json.JSONDecodeError as e:
        raise AIConfigError(
            f"Gemini returned malformed JSON after retrying "
            f"(finish_reason={_finish_reason(resp2)}): {e}"
        )


def _grok_client() -> Optional[openai.OpenAI]:
    key = os.environ.get("XAI_API_KEY")
    if not key:
        return None
    return openai.OpenAI(api_key=key, base_url=GROK_BASE_URL)


def _call_json_grok(system: str, user: str, schema: dict, max_output_tokens: int) -> dict:
    """Fallback path used only when Gemini has already failed. xAI's Grok API
    is OpenAI-compatible, so we reuse the same client shape. We include our
    JSON schema in the prompt itself (Grok's JSON mode guarantees valid JSON
    syntax, but not a specific shape the way Gemini's response_schema does),
    then validate/retry the same way we do for Gemini."""
    client = _grok_client()
    if client is None:
        raise AIConfigError("Grok fallback unavailable: XAI_API_KEY is not set.")

    schema_hint = f"\nYour JSON response MUST match this exact shape: {json.dumps(schema)}"

    def _ask(sys_prompt: str, tokens: int):
        try:
            return client.chat.completions.create(
                model=GROK_MODEL,
                max_tokens=tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": sys_prompt + schema_hint},
                    {"role": "user", "content": user},
                ],
            )
        except openai.APIError as e:
            raise AIConfigError(f"Grok API error: {e}")

    resp = _ask(system, max_output_tokens)
    raw = (resp.choices[0].message.content or "").strip()
    cleaned = _extract_json_object(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    stricter = system + "\nCRITICAL: return ONLY the JSON object, nothing else. Make sure it is complete and valid JSON matching the required shape."
    resp2 = _ask(stricter, max_output_tokens * 2)
    raw2 = (resp2.choices[0].message.content or "").strip()
    cleaned2 = _extract_json_object(raw2)
    try:
        return json.loads(cleaned2)
    except json.JSONDecodeError as e:
        raise AIConfigError(f"Grok returned malformed JSON after retrying: {e}")


def _call_json(system: str, user: str, schema: dict, max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS) -> dict:
    """Gemini is always tried first - this is the same path that already
    works today, unchanged. Only if Gemini fails outright (after its own
    internal retries) do we fall back to Grok, and only if XAI_API_KEY is
    configured. If it isn't set, behavior is identical to before this
    fallback existed."""
    try:
        return _call_json_gemini(system, user, schema, max_output_tokens)
    except AIConfigError as gemini_error:
        if not os.environ.get("XAI_API_KEY"):
            raise
        try:
            return _call_json_grok(system, user, schema, max_output_tokens)
        except Exception as grok_error:
            raise AIConfigError(
                f"Both AI providers failed. Gemini: {gemini_error} | Grok fallback: {grok_error}"
            )


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
    return _call_json(SYSTEM_BASE, prompt, SUMMARY_SCHEMA)


def analyze_risks(clauses) -> dict:
    prompt = f"""Review these clauses for a non-lawyer reader. Identify concerning clauses, financial obligations, penalties, termination conditions, notice periods, renewal/auto-renewal clauses, confidentiality obligations, non-compete/non-solicitation, dispute-resolution clauses (arbitration, jury trial waivers), and missing/inconsistent information.
Return ONLY a JSON object:
{{ "risks": [
  {{"clauseId":"C_","title":"short title","category":"Financial Obligation|Penalty|Termination|Notice Period|Renewal|Confidentiality|Non-Compete|Dispute Resolution|Missing/Inconsistent|Other","severity":"high|medium|standard","explanation":"one plain-language sentence"}}
] }}
At most 10 items, high severity first.

CLAUSES:
{_clause_block(clauses)}"""
    return _call_json(SYSTEM_BASE, prompt, RISKS_SCHEMA)


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
    return _call_json(SYSTEM_BASE, prompt, CHAT_SCHEMA)


def next_steps(retrieved_clauses, question: Optional[str]) -> dict:
    context = f'The user asked: "{question}"' if question else "The user wants general next steps for handling this document."
    prompt = f"""{context}
Based only on the clauses below, suggest general informational next steps - never definitive legal advice, never a predicted outcome.
Return ONLY a JSON object:
{{"steps": ["up to 4 short, concrete next steps, e.g. 'Review Clause 7', 'Collect proof of payment history', 'Ask a lawyer about the early-termination fee'"], "rationale": "one sentence on why these steps, or null"}}

CLAUSES:
{_clause_block(retrieved_clauses)}"""
    return _call_json(SYSTEM_BASE, prompt, NEXT_STEPS_SCHEMA)


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
    return _call_json(SYSTEM_BASE, prompt, DIFF_SCHEMA)


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
    return _call_json(SYSTEM_BASE, prompt, LAWYER_PREP_SCHEMA)
