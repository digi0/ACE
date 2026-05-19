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

# Refresh the PSU academic calendar JSON
python -m backend.services.calendar_scraper

# Quick test of vault loading
python test_vault.py

# Rule extraction tests
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

Backend `.env` at the repo root:
```
OPENAI_API_KEY=sk-...
CLERK_SECRET_KEY=sk_test_... or sk_live_...
LOG_LEVEL=INFO          # optional
ALLOWED_ORIGINS=...     # optional CSV; also serves as Clerk authorized_parties
DATABASE_URL=...        # optional; injected by Railway in prod, falls back to SQLite locally
```

Frontend `.env` in `frontend/`:
```
VITE_CLERK_PUBLISHABLE_KEY=pk_test_... or pk_live_...
VITE_API_URL=http://127.0.0.1:8000   # optional, defaults to this
```

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

Upload → `student_doc_service.py` extracts PDF text → `audit_parser_service.py` parses blocks (`parse_whatif_blocks`) → result persisted to the `user_docs` table keyed by Clerk uid. Reads go through `get_current_student_doc(user_id, db)` — there is no in-memory cache; every request queries the DB. The `/dashboard` endpoint transforms `audit_parse` into credit summaries and remaining requirements.

### Auth + per-user state

Clerk replaces what used to be Firebase. The model is:

- Frontend `<ClerkProvider>` wraps the app in `main.jsx`. `AuthContext.jsx` is a thin shim around `useUser()` / `useAuth()` hooks that exposes `{ user, syncData, signOut }` so consumers don't talk to Clerk directly.
- `api.js` (`apiFetch` / `apiStream`) reads the bearer token from `window.Clerk.session.getToken()` — plain modules don't go through React hooks.
- Backend `clerk_auth.py` verifies session JWTs via the official `clerk-backend-api` SDK's `authenticate_request()`. `get_current_user` returns `{uid}` — Clerk's default session JWT only carries `sub`.
- `/auth/sync` is the single source-of-truth round-trip on login: it upserts the User row (calling `fetch_user_details(uid)` to pull email + display name from the Clerk users API) AND returns `{major, has_doc}` so the frontend can hydrate without a second request.

**Important pattern to preserve:** do not add a separate `GET /user/major` (or similar per-field endpoint) and call it on user-state-change. We did, and it raced against `/auth/sync` — the GET fired before the User row existed, returned null, and made the major-selection modal reappear on every fresh browser. The fix is to keep all post-login state piggybacking on the `/auth/sync` response and gate effects in `App.jsx` on `syncData != null`.

### Database

SQLAlchemy ORM in `backend/models.py`. `backend/database.py` picks SQLite locally (`backend/data/ace_users.db`) and PostgreSQL on Railway (via `DATABASE_URL`, with the `postgres://` → `postgresql://` rewrite needed by SQLAlchemy).

Tables:
- `users` — `id` is the Clerk user ID (sub claim), plus `email`, `display_name`, `selected_major`, timestamps
- `user_docs` — uploaded Degree Audit / What-If, one-per-user in practice; cascade-deletes with the user
- `conversations` + `messages` — chat history, FK chain cascades

Schema is created by `Base.metadata.create_all(bind=engine)` at FastAPI startup. There is no Alembic migration in use yet — adding a non-nullable column to an existing prod Postgres table will require either a one-off `ALTER TABLE` or wiring up Alembic. Existing nullable columns are safe to add via `create_all` (no-ops if the table exists; new columns must be defaulted).

### Frontend

Single-page React app (`frontend/src/`). State lives in `App.jsx`. Key patterns:
- Auth via Clerk (`AuthContext.jsx` wraps `@clerk/clerk-react`); prebuilt `<SignIn />` / `<SignUp />` rendered on LoginPage with `appearance.elements` overrides to fit the surrounding card
- Chat uses SSE via `POST /chat/stream`; responses stream token-by-token
- Follow-up chips are driven by the `intent` field in the `done` SSE event
- `activeView` state switches between chat, dashboard, resources, gen-ed, and tool panels (GPA calc, calendar, checklist, prereq map)
- Sidebar widgets are configurable and persisted to `localStorage` under `ace_widgets3`
- Conversations are persisted to `localStorage` keyed by Clerk user ID (`ace_chats_{uid}`)
- `SparklesCore.jsx` is a manual port of Aceternity's Sparkles (`@tsparticles/react` + `@tsparticles/slim`) — NOT installed via shadcn, so the rest of the app's plain-CSS stack stays Tailwind-free

### Key config (`backend/config.py`)

- `VAULT_FILE` — path to the Excel knowledge base
- `INDEX_FILE` — path to the serialized embedding index (`backend/data/ace_index.pkl`)
- `OPENAI_CHAT_MODEL` — `gpt-4o-mini`
- `OPENAI_EMBEDDING_MODEL` — `text-embedding-3-small`
- `CHUNK_SIZE` / `CHUNK_OVERLAP` — word-level chunking for PDF ingestion

### Deployment

Backend is deployed on Railway; frontend on Vercel. The committed index file avoids Railway's cold-start build timeout. Vercel rewrites in `frontend/vercel.json` are SPA-fallback only (the old Firebase auth-handler proxy was removed with the Clerk migration).
