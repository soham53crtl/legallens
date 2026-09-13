# Contributing to LegalLens

## Setup

See the "Running it" section in the [README](README.md) for backend and frontend setup.

## Before opening a PR

```bash
# backend
cd backend && python -m pytest tests/ -v

# frontend
cd frontend && npm run lint && npm run build
```

Both run automatically in CI on every push, but running them locally first saves a round
trip.

## Code layout

- `backend/app/extraction.py` — file → raw text (PDF/DOCX/TXT)
- `backend/app/clauses.py` — raw text → numbered clause chunks
- `backend/app/retrieval.py` — TF-IDF vector index + retrieval over clauses
- `backend/app/diffing.py` — computed clause-level diff between two documents
- `backend/app/ai.py` — every Claude API call and prompt lives here, nowhere else
- `backend/app/storage.py` — session-isolated in-memory document store
- `backend/app/main.py` — FastAPI routes, thin — logic belongs in the modules above
- `frontend/lib/api.ts` — the only file that should call `fetch` against the backend
- `frontend/lib/store.tsx` — shared session/document state across pages

## A few things this project cares about

- **Never let the LLM invent a fact it can check.** `diffing.py` computes the diff before
  any AI call touches it; `ai.py`'s system prompt requires clause-ID citations and an
  explicit "not addressed" answer when the document doesn't cover something. If you add a
  feature that calls the model, keep that pattern.
- **No secrets in the repo.** `.env` / `.env.local` are gitignored — use the `.example`
  files as templates.
- **Session isolation is a security property, not a UI nicety.** If you touch
  `storage.py`, keep (and extend) `test_document_isolation_across_sessions`.
