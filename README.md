# ACE — Academic Counselling Engine

> An AI academic advisor for Penn State students. Ask about courses, requirements, deadlines, and policies — or upload your Degree Audit / What-If report and get answers grounded in *your* actual progress.

ACE pairs **RAG** (retrieval over advising records, handbooks, and PSU bulletins) with **personalized analysis** of a student's uploaded academic documents. It covers all **749** Penn State majors via structured program data, with deeper support for the College of IST / Computer Science programs the engine was first built around.

🌐 **Live:** [acecollege.app](https://acecollege.app) (waitlist) · the product runs at `app.acecollege.app` (currently behind a pilot access gate)

---

## Architecture

```
ACE_vlt.xlsx  +  CMPSC/DTSCE handbook PDFs  +  PSU bulletins (scraped)
       └──────────── vault_loader.py ───────────────────┘
                          │
            index_service.py  →  ace_index.pkl   (OpenAI embeddings, committed)
                          │
            embedding_service.py   (cosine sim + keyword + course-code boosts)
                          │
            chat_service.py  →  OpenAI gpt-4o-mini   (streaming SSE)
                          │
            main.py (FastAPI)  →  React frontend
```

**Knowledge base — three source types**, merged by `vault_loader.py`, each weighted differently per question intent:

| `source_type`  | Origin                                       |
|----------------|----------------------------------------------|
| `excel_vault`  | `ACE_vlt.xlsx` — curated advising records    |
| `pdf_handbook` | CMPSC / DTSCE handbook PDFs (chunked)        |
| `web_bulletin` | PSU bulletin pages scraped at index time     |

The pre-built index (`backend/data/ace_index.pkl`) is committed so production deploys skip the cold-start embedding rebuild.

**Intent routing** — `detect_question_intent()` classifies every question (`courses`, `student_progress`, `substitution`, `etm`, `transfer`, `contact`, `gen_ed`, `deadline`, `wellbeing`, `general`). The intent decides which sources are prioritized, whether deterministic snippets (deadlines, gen-ed tables, campus resources) are injected, and — when a student doc is uploaded — routes `student_progress` straight to a deterministic answer that bypasses the LLM.

**Student documents** — upload → `student_doc_service.py` extracts PDF text → `audit_parser_service.py` parses blocks → result persisted to the `user_docs` table keyed by Clerk uid. The `/dashboard` endpoint turns that parse into credit summaries and remaining requirements; the GPA, Gen-Ed, Prereq-Map, and Plan tools read from it too.

---

## Tech stack

| Layer       | Stack                                                             |
|-------------|------------------------------------------------------------------|
| Frontend    | React 19 + Vite, plain CSS (design tokens), Clerk, lucide-react   |
| Backend     | FastAPI + Uvicorn, SQLAlchemy, OpenAI SDK, pypdf, BeautifulSoup   |
| Auth        | [Clerk](https://clerk.com) (session-JWT verification server-side) |
| Model       | OpenAI `gpt-4o-mini` (chat) · `text-embedding-3-small` (index)    |
| Database    | SQLite locally · PostgreSQL in production (via `DATABASE_URL`)    |
| Deploy      | Backend → Railway · Frontend & landing → Vercel                  |

---

## Repository layout

```
backend/            FastAPI app
  main.py             routes + app wiring
  services/           chat, embeddings, indexing, audit parsing, scrapers, cost
  data/               vault loader, committed index (ace_index.pkl), JSON catalogs
  models.py           SQLAlchemy ORM (users, user_docs, conversations, messages)
  clerk_auth.py       Clerk session-JWT verification
  eval/               retrieval/answer evaluation harness
frontend/           React + Vite single-page app (the product)
landing/            React + Vite waitlist / marketing site (acecollege.app)
ACE_vlt.xlsx        Excel knowledge base
*-handbook-*.pdf    CMPSC / DTSCE advising handbooks
requirements.txt    backend Python deps
Procfile            Railway start command
```

---

## Getting started

**Prerequisites:** Python 3.11+, Node 18+, an OpenAI API key, and a Clerk application (test keys are fine for local dev).

### Backend

```bash
# from repo root
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# create .env (see below), then:
uvicorn backend.main:app --reload          # http://127.0.0.1:8000
```

`.env` at the repo root:

```bash
OPENAI_API_KEY=sk-...
CLERK_SECRET_KEY=sk_test_...        # or sk_live_... in prod
LOG_LEVEL=INFO                      # optional
ALLOWED_ORIGINS=...                 # optional CSV; also Clerk authorized_parties (no spaces around commas)
DATABASE_URL=...                    # optional; Railway injects in prod, falls back to SQLite locally
```

### Frontend

```bash
cd frontend
npm install
npm run dev                          # Vite dev server
```

`frontend/.env`:

```bash
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...   # or pk_live_... in prod
VITE_API_URL=http://127.0.0.1:8000       # optional, defaults to this
```

### Landing site (optional)

```bash
cd landing && npm install && npm run dev
```

---

## Common tasks

```bash
# Rebuild the vector index (after changing vault / handbook / bulletin data)
python -c "from backend.services.index_service import build_index; build_index()"

# Refresh the PSU academic calendar JSON
python -m backend.services.calendar_scraper

# Estimate OpenAI cost for N users / M messages
python -m backend.scripts.estimate_cost --users 100 --msgs 20

# Backend tests
python -m pytest backend/test_rules.py -v

# Frontend
cd frontend && npm run build      # production build
cd frontend && npm run lint       # eslint
```

---

## How auth works

Clerk is the single source of truth. The frontend `<ClerkProvider>` wraps the app; `AuthContext.jsx` is a thin shim over Clerk's hooks. On login, the **one** round-trip is `POST /auth/sync` — it upserts the user row (pulling email + name from the Clerk users API) and returns `{ major, has_doc }` so the UI hydrates without a second request. The backend verifies session JWTs with the official `clerk-backend-api` SDK; `get_current_user` returns `{ uid }` (the `sub` claim).

> **Note:** all post-login state piggybacks on the `/auth/sync` response by design — adding a separate per-field GET that fires on user-state-change will race against `sync` and break the major-selection flow.

---

## Database

SQLAlchemy ORM (`backend/models.py`); `backend/database.py` picks SQLite locally and PostgreSQL on Railway. Tables: `users` (keyed by Clerk uid), `user_docs` (uploaded audit, one per user), and `conversations` + `messages` (chat history). Schema is created at startup via `Base.metadata.create_all`. No Alembic migrations are wired up yet — adding a non-nullable column to prod Postgres needs a manual `ALTER TABLE` or Alembic.

---

## Deployment

- **Backend** → Railway (`Procfile`: `uvicorn backend.main:app`). The committed index avoids the build-time embedding rebuild.
- **Frontend & landing** → Vercel (separate projects; `frontend/vercel.json` is SPA-fallback only).
- Set production secrets as environment variables on each platform — never commit `.env`, the local SQLite DB, or uploaded documents (all gitignored).

---

*ACE is an independent student project and is not officially affiliated with or endorsed by The Pennsylvania State University. Always confirm academic decisions with a human advisor.*
