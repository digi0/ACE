# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ACE (Academic Counselling Engine) is a Penn State academic advisor chatbot for CMPSC (Computer Science) and DTSCE (Computational Data Sciences) students. It combines RAG (retrieval-augmented generation) over advising records with personalized analysis of uploaded student documents (Degree Audits, What-If Reports).

## Commands

### Backend

```bash
# Run the FastAPI backend (from repo root)
uvicorn backend.main:app --reload

# Run backend with a specific port
uvicorn backend.main:app --reload --port 8000

# Rebuild the vector index (needed after changing vault/handbook data)
python -c "from backend.services.index_service import build_index; build_index()"

# Run a quick test of vault loading
python test_vault.py

# Run rule extraction tests
python -m pytest backend/test_rules.py -v
```

### Frontend

```bash
# Install and start dev server
cd frontend && npm install && npm run dev

# Build for production
cd frontend && npm run build

# Lint
cd frontend && npm run lint
```

### Environment

The backend requires a `.env` file at the repo root:
```
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO   # optional, defaults to INFO
```

The frontend reads `VITE_API_URL` (e.g. `http://127.0.0.1:8000`) from a `.env` file in `frontend/`. If unset, it falls back to `http://127.0.0.1:8000`.

## Architecture

### Data flow

```
ACE_vlt.xlsx  +  CMPSC-handbook-*.pdf  +  PSU bulletins (scraped)
       └──────── vault_loader.py ────────────────────┘
                        │
               index_service.py (builds ace_index.pkl with OpenAI embeddings)
                        │
               embedding_service.py (semantic_search with cosine sim + keyword + course-code boosts)
                        │
               chat_service.py ──► OpenAI gpt-4o-mini (streaming SSE)
                        │
               main.py (FastAPI) ──► React frontend
```

### Knowledge base (three source types)

Records in the index carry a `source_type` field that drives retrieval weighting in `select_top_records()`:

| `source_type`   | Origin                                   |
|-----------------|------------------------------------------|
| `excel_vault`   | `ACE_vlt.xlsx` (sheet: PSU CMPSC)        |
| `pdf_handbook`  | CMPSC / DTSCE handbook PDFs (chunked)    |
| `web_bulletin`  | PSU bulletin pages scraped at index time |

`vault_loader.py` merges all three sources. The pre-built index (`backend/data/ace_index.pkl`) is committed to avoid cold-start timeouts on Railway.

### Intent routing

`detect_question_intent()` in `chat_service.py` classifies every question into one of: `courses`, `student_progress`, `substitution`, `etm`, `transfer`, `contact`, `gen_ed`, `deadline`, `wellbeing`, `general`. The intent:

- Controls which source types are prioritised by `select_top_records()`
- Determines whether hardcoded snippets are injected (deadline dates, gen-ed tables, campus resources, degree-audit advisory)
- Triggers the deterministic path for `student_progress` when a student doc is uploaded (bypasses LLM)

### Student document pipeline

Upload → `student_doc_service.py` extracts PDF text → `audit_parser_service.py` parses blocks (`parse_whatif_blocks`) → structured result stored in module-level `_current_student_doc` dict (in-memory, single user). The `/dashboard` endpoint transforms `audit_parse` into credit summaries and remaining requirements.

### Frontend

Single-page React app (`frontend/src/`). State lives in `App.jsx`. Key patterns:
- Auth via Firebase (`AuthContext.jsx`/`firebase.js`), Google sign-in
- Chat uses SSE via `POST /chat/stream`; responses stream token-by-token
- Follow-up chips are driven by the `intent` field in the `done` SSE event
- `activeView` state switches between chat, dashboard, resources, gen-ed, and tool panels (GPA calc, calendar, checklist, prereq map)
- Sidebar widgets are configurable and persisted to `localStorage` under `ace_widgets3`
- Conversations are persisted to `localStorage` keyed by Firebase UID (`ace_chats_{uid}`)

### Key config (`backend/config.py`)

- `VAULT_FILE` — path to the Excel knowledge base
- `INDEX_FILE` — path to the serialized embedding index (`backend/data/ace_index.pkl`)
- `OPENAI_CHAT_MODEL` — `gpt-4o-mini`
- `OPENAI_EMBEDDING_MODEL` — `text-embedding-3-small`
- `CHUNK_SIZE` / `CHUNK_OVERLAP` — word-level chunking for PDF ingestion

### Deployment

Backend is deployed on Railway; frontend on Vercel (or similar). The committed index file avoids Railway's cold-start build timeout.
