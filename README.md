# LegalLens

[![Backend tests](https://github.com/soham53crtl/legallens/actions/workflows/backend-tests.yml/badge.svg)](https://github.com/soham53crtl/legallens/actions/workflows/backend-tests.yml)
[![Frontend build](https://github.com/soham53crtl/legallens/actions/workflows/frontend-build.yml/badge.svg)](https://github.com/soham53crtl/legallens/actions/workflows/frontend-build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An AI-powered legal document assistant built for the PromptWars "AI for Legal Assistance &
Access" challenge. LegalLens helps a non-lawyer understand a contract, flags what deserves
attention, lets them interrogate the document directly, compares two versions of it, and
prepares them to talk to an actual lawyer.

**LegalLens provides general legal information and document assistance. It does not provide
legal advice and does not replace a qualified legal professional.**

> Update the two badge URLs above if you push this to a different GitHub repo path than
> `soham53crtl/legallens`.

## Project structure

```
legallens/
├── backend/                 FastAPI service
│   ├── app/
│   │   ├── main.py          routes
│   │   ├── extraction.py    PDF/DOCX/TXT → raw text
│   │   ├── clauses.py       raw text → numbered clause chunks
│   │   ├── retrieval.py     TF-IDF vector index + retrieval
│   │   ├── diffing.py       computed clause-level diff
│   │   ├── ai.py            every Claude API call + prompt
│   │   ├── storage.py       session-isolated in-memory store
│   │   ├── models.py        Pydantic schemas
│   │   └── demo.py          sample lease + renewal version
│   ├── tests/                26 pytest tests (AI calls mocked)
│   └── requirements.txt
├── frontend/                 Next.js 14 (App Router) + Tailwind
│   ├── app/                  landing, dashboard, analysis, chat, compare, lawyer-prep
│   ├── components/           Nav, UploadModal, DisclaimerBar
│   └── lib/                  api.ts (fetch client), store.tsx (shared state), types.ts
├── .github/workflows/        CI: backend tests + frontend build, on every push
├── LICENSE                   MIT
└── CONTRIBUTING.md
```

## Architecture

```
frontend/   Next.js 14 (App Router) + Tailwind — all 7 views, calls the API below
backend/    FastAPI — extraction, chunking, retrieval, diffing, and the LLM layer
```

This is a genuine two-service architecture (not a single HTML file calling an API
directly): the frontend never talks to Anthropic, only to the FastAPI backend, which is
where the API key lives.

### Request flow for one document

```
Upload → extraction.py (pypdf / python-docx / plain text)
       → clauses.py (numbered-clause or paragraph chunking, stable IDs: C1, C2, …)
       → retrieval.py (TF-IDF vector index built over the document's own clauses)
       → storage.py (session-isolated in-memory store)

Ask a question → retrieval.py finds the top-k relevant clauses (vector search)
               → ai.py sends only those clauses to Claude, asks for a grounded,
                 cited, JSON answer

Compare two documents → diffing.py computes the actual clause-level diff
                       (difflib alignment + regex-based amount/date change detection)
                      → ai.py is only used to phrase that pre-computed diff in
                        plain language — it cannot invent a difference itself
```

### Why TF-IDF instead of a neural embedding model

The brief asks for "embeddings/vector search for document retrieval." Rather than calling
an external embeddings API for documents that are already fully available locally, each
clause is embedded as a TF-IDF vector over the document's own vocabulary and retrieved by
cosine similarity (`backend/app/retrieval.py`). This is a real, computed vector-search
step — deterministic, fast, and requiring no additional network dependency — and it's
what many production retrieval systems still use as a lexical stage. Its known limitation
is that it matches shared vocabulary, not meaning (a query about "my dog" won't reliably
find a clause that only says "pets" and never "dog") — this tradeoff is documented and
directly tested in `test_retrieval_is_lexical_not_semantic`. Swapping in a neural embedding
model later is a contained change to `retrieval.py` alone.

### Why the diff is computed, not just AI-described

`diffing.py` aligns clauses between two document versions using `difflib.SequenceMatcher`
and flags amount/date changes with regex — all before any LLM call. The LLM
(`ai.describe_diff`) is only allowed to phrase the differences that were already found; it
cannot report an "added clause" that computed diffing didn't detect. This is the
difference between a comparison feature you can trust and one that's just an AI guessing
at two documents.

### Security / document isolation

Every document lives under a server-generated `session_id` that the client cannot choose
or guess (`backend/app/storage.py`). Every read requires both `session_id` and `doc_id` to
match, so a document uploaded in one browser session is a 404 — not just hidden in the UI
— from any other. Sessions expire after an hour of inactivity. This is enforced with a
test (`test_document_isolation_across_sessions`), not just asserted in the UI copy.

## Feature coverage

| Brief requirement | Where it lives |
|---|---|
| Document upload (PDF/DOCX/TXT) | `backend/app/extraction.py`, upload modal |
| AI Legal Simplifier | `ai.analyze_summary` → Analysis page |
| Risk & Clause Scanner (🔴🟠🟢) | `ai.analyze_risks` → Analysis page |
| "What Am I Agreeing To?" | Analysis page obligations/rights/payments/etc. |
| Ask Your Document | `/chat` endpoint, grounded + cited, Chat page |
| Contract Comparison | `diffing.py` + `ai.describe_diff`, Compare page |
| Important Dates & Deadlines | `importantDates` in the summary schema, timeline UI |
| Next-Step Assistant | **Standalone** `/next-steps` endpoint (not folded into chat) |
| Lawyer Preparation Mode | `/lawyer-prep` endpoint, shareable/downloadable sheet |
| Disclaimer always visible | `DisclaimerBar` component, fixed on every page |
| Never fabricate / cite clauses / state uncertainty | Enforced in every prompt's system message (`ai.SYSTEM_BASE`) |
| Protect uploaded docs from other users | Session-isolated storage, tested |
| Demo without uploading | `/documents/demo` (sample lease + a renewal version for Compare) |

## Running it

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then put a real GROQ_API_KEY in .env
export $(cat .env | xargs)
uvicorn app.main:app --reload --port 8000
```
Without `GROQ_API_KEY` set, every non-AI endpoint (upload, demo load, clause
retrieval) still works — only the LLM-backed endpoints return a clear `503` rather than
crashing. This is intentional and tested (`test_ai_config_error_returns_503`).

### Frontend
```bash
cd frontend
cp .env.local.example .env.local   # points at http://localhost:8000 by default
npm install
npm run dev
```
Open http://localhost:3000.

### Tests
```bash
cd backend
python3 -m pytest tests/ -v
```
26 tests covering clause splitting, TF-IDF retrieval, computed diffing, extraction, and
every API route (with AI calls mocked, so the suite runs with no API key and verifies the
app's own logic rather than Anthropic's).

## Pushing this to GitHub

This directory is already a git repository with an initial commit (see below). To push it:

```bash
git remote add origin https://github.com/soham53crtl/legallens.git
git branch -M main
git push -u origin main
```

Then add `GROQ_API_KEY` as a repository secret if you wire up a deploy workflow, and
set the same variable in your Render/hosting provider's environment — never in the repo.

## Deploying

Same pattern as other projects in this portfolio: frontend on Vercel
(`NEXT_PUBLIC_API_URL` pointed at the deployed backend), backend on Render with
`GROQ_API_KEY` set as a secret environment variable. `storage.py`'s in-memory store
is the one piece to swap for Redis/Postgres if you need documents to survive a backend
restart — the session_id/doc_id access-check pattern carries over unchanged.

## Known limitations (honest, not hidden)

- TF-IDF retrieval is lexical, not semantic — see above.
- The in-memory store means a backend restart clears all sessions; fine for a hackathon
  demo, not for production without swapping the storage backend.
- `describe_diff` only runs the LLM over already-computed differences, but its phrasing of
  *why* something matters is still a generated summary, like every other AI-assisted field
  in the app — treat it as informational, same as the rest of LegalLens.
