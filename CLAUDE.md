# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ACE (Academic Counselling Engine) is a Penn State academic advisor chatbot for CMPSC (Computer Science) and DTSCE (Computational Data Sciences) students. It combines RAG (retrieval-augmented generation) over advising records with personalized analysis of uploaded student documents (Degree Audits, What-If Reports).

## Brand — read `brand/BRAND.md` before any visual work

The logo and design language were rebuilt in July 2026 and are **locked**: the mark is
a lowercase `a` leaning −11° with a level emerald period, and the language is **Zero
Chroma** (six greys, no hue, plus the period). Design tokens live in
`brand/tokens.css` — import them, don't retype hex values.

The one rule that governs every screen: **emerald `#00875A` appears once per view,
and it is always the period** (send button, due date, destination, done).

The mark has shipped into `frontend/` and `landing/`, but **the landing and product UI
are still on the old blue brand** — remodelling them around Zero Chroma is the next
piece of work. `brand/BRAND.md` §5 is the pickup point, with the migration path and the
open questions. `brand/playbook.html` is the go-to-market playbook — read it before
writing any marketing copy.

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

# Data build steps (never run at request time — see the runbook in README)
python -m backend.data.policy_extractor    # handbook PDFs → policies.json
python -m backend.services.calendar_scraper
python -c "from backend.services.index_service import build_index; build_index()"

# Self-checks (plain asserts / print scripts — pytest is not installed)
python -m backend.test_policies   # policies.json schema + snippet relay
python -m backend.test_routing    # major classification, scope filter, record selection
python -m backend.test_rules      # dumps extracted requirement rules
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
programs.json (749) + courses.json (9,439)  ──►  program_service.py
       │  structured path — every major, and every tool
       │
CMPSC/DTSCE handbook PDFs ──► policy_extractor.py ──► policies.json ──► policy_service.py
       │  policy path — CMPSC/DTSCE only, lookup by (intent, scope), no retrieval
       │
CMPSC-handbook-*.pdf  +  PSU bulletins (scraped)     RAG path — CMPSC/DTSCE only
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

### Knowledge base (two grounding paths)

**Structured data is the backbone.** `backend/data/programs.json` (749 programs — prescribed/additional requirements with min grades, semester suggested plans, gen-ed overlap, bulletin URL) and `courses.json` (9,439 course records) are read by `program_service.py`. They serve every major and back every tool (prereq map, gen-ed explorer, suggested plan, dashboard).

**Handbook policies are structured, not retrieved.** `backend/data/policies.json` (46 rules) is built offline by `backend/data/policy_extractor.py` — an LLM extraction pass over the handbook PDFs (gpt-4o-mini, temperature 0, strict JSON schema, ~$0.006/run) that emits one record per rule with `scope` (`cs`/`ds`), `topic`, the handbook's own wording, supporting details, named courses, and page-level source. `backend/services/policy_service.py` relays them into the prompt via `INTENT_TOPICS[intent]` → topic list → `get_policies(scope, topics)`; there is no embedding or similarity step on this path. Regenerate with `python -m backend.data.policy_extractor` whenever the PDFs change, and diff the output before committing (extraction is not bit-for-bit reproducible).

**The RAG index is the remaining CMPSC/DTSCE fallback** (73 records) — it exists for procedural content the structured data lacks: Entrance-to-Major rules, petitions, substitution process, department contacts. Records carry a `source_type` that drives weighting in `select_top_records()`:

| `source_type`   | Records | Origin                                   |
|-----------------|---------|------------------------------------------|
| `pdf_handbook`  | 47      | CMPSC / DTSCE handbook PDFs (chunked)    |
| `web_bulletin`  | 26      | PSU bulletin pages scraped at index time |

**Fixed alongside the retirement:** `classify_major()` used to read `if "computer science" in nl and "engineering" not in nl`, which excluded `Computer Science, B.S. (Engineering)` — the University Park program the CMPSC handbook and `BULLETIN_URL` actually document. That one major silently fell through to structured-only answers. The `engineering` exclusion is gone; don't re-add it.

`classify_major()` gates which paths run — `cs`/`ds` get policies + RAG + structured; every other major, and any student with no major declared, gets structured only (`suppress_cs_ds`), so CS/DS handbook text can't leak into an unrelated major's answer. Within CS/DS, `filter_records_by_scope()` runs between `semantic_search(top_k=16)` and `select_top_records()` and drops the other program's records — the index holds CMPSC and DTSCE side by side, so without it a DS student gets cited to the CMPSC handbook. The pre-built index (`backend/data/ace_index.pkl`) is committed to avoid cold-start timeouts on Railway.

**Retired (July 2026):** an `excel_vault` source (`ACE_vlt.xlsx`, sheet "PSU CMPSC") plus `vault_service.py` and the `/vault` + `/vault/search` endpoints. The sheet had no `Content` column, so all 13 records embedded and retrieved as empty text while still occupying the top context slots for the `etm` / `transfer` / `contact` / `deadline` / `general` intents. `vault_service` also ran `load_psu_cmpsc_vault()` at import time, so every backend boot re-parsed the PDFs and re-scraped two PSU URLs. Don't reintroduce either pattern — put new advising knowledge in the structured JSON.

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

- `INDEX_FILE` — path to the serialized embedding index (`backend/data/ace_index.pkl`)
- `OPENAI_CHAT_MODEL` — `gpt-4o-mini`
- `OPENAI_EMBEDDING_MODEL` — `text-embedding-3-small`
- `CHUNK_SIZE` / `CHUNK_OVERLAP` — word-level chunking for PDF ingestion

### Deployment

Backend is deployed on Railway; frontend on Vercel. The committed index file avoids Railway's cold-start build timeout. Vercel rewrites in `frontend/vercel.json` are SPA-fallback only (the old Firebase auth-handler proxy was removed with the Clerk migration).
