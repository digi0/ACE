import logging
import os
import re
import time
from datetime import datetime, timezone

from fastapi import FastAPI, Query, Form, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.config import UPLOAD_DIR, LOG_LEVEL
from backend.database import engine, Base, get_db
from backend import models  # noqa: F401 — registers models with Base
from backend.clerk_auth import (
    get_current_user,
    get_optional_user,
    get_current_user_any,
    fetch_user_details,
)
from backend.services.chat_service import ask_advisor_stream
from backend.services.transcript_service import set_rating, review_summary
from backend.services.student_doc_service import (
    load_student_document,
    clear_student_document,
    get_current_student_doc,
    has_student_doc,
    cleanup_upload_dir,
    set_user_major,
    get_user_major,
)
from backend.services.program_service import (
    get_all_programs,
    get_course,
    build_gen_ed_response,
    build_prereq_map,
    build_suggested_plan,
    search_programs,
)
from backend.services.calendar_scraper import (
    load_calendar,
    refresh_calendar,
    CALENDAR_FILE,
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Create all tables (safe to call repeatedly — only creates if missing)
Base.metadata.create_all(bind=engine)


def _ensure_columns():
    """Add columns that `create_all` cannot, because their table already exists.

    `create_all` only creates *missing tables* — it never alters an existing one.
    So a new nullable column on a table already live in prod Postgres needs an
    explicit ALTER. Idempotent and fail-soft: a boot must not die over this.
    """
    from sqlalchemy import inspect, text

    wanted = {("messages", "rating"): "INTEGER"}
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        with engine.begin() as conn:
            for (table, column), coltype in wanted.items():
                if table not in tables:
                    continue  # create_all just made it, with the column included
                existing = {c["name"] for c in inspector.get_columns(table)}
                if column in existing:
                    continue
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))
                logger.info("_ensure_columns | added %s.%s", table, column)
    except Exception as e:
        logger.error("_ensure_columns | skipped: %s", e, exc_info=True)


_ensure_columns()

# ── CORS ──────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:8000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Request models ────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=8000)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    history: List[ChatMessage] = Field(default_factory=list)
    # Client-minted conversation UUID. Optional: without it the exchange still
    # streams normally, it just isn't recorded.
    conversation_id: str | None = Field(default=None, max_length=64)


class RatingRequest(BaseModel):
    rating: int = Field(..., ge=-1, le=1)


# ── Chat rate limit ───────────────────────────────────────────────────────────
# One student shouldn't be able to torch the OpenAI budget. Sliding window of
# per-user request timestamps.
# ponytail: in-process dict — resets on deploy and is per-worker, so N workers
# allow N× the limit. Move to a DB/Redis counter if we ever run more than one.
CHAT_RATE_LIMIT = int(os.getenv("CHAT_RATE_LIMIT", "30"))      # requests
CHAT_RATE_WINDOW = int(os.getenv("CHAT_RATE_WINDOW", "3600"))  # seconds
_chat_hits: dict[str, list[float]] = {}


def check_chat_rate_limit(user_id: str):
    """Raise 429 if this user is over the window. No-op when the limit is 0."""
    if CHAT_RATE_LIMIT <= 0:
        return
    now = time.monotonic()
    hits = [t for t in _chat_hits.get(user_id, []) if now - t < CHAT_RATE_WINDOW]
    if len(hits) >= CHAT_RATE_LIMIT:
        retry_after = int(CHAT_RATE_WINDOW - (now - hits[0])) + 1
        _chat_hits[user_id] = hits
        logger.warning("chat rate limit hit | user_id=%r", user_id)
        raise HTTPException(
            status_code=429,
            detail=f"You've hit the message limit ({CHAT_RATE_LIMIT}/hour). Try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )
    hits.append(now)
    _chat_hits[user_id] = hits


class MajorRequest(BaseModel):
    major: str = Field(..., min_length=1, max_length=500)


# ── Public endpoints ──────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "PSU Academic Advisor Backend Running"}


@app.get("/programs")
def list_programs(
    q: str = Query(default=None),
    college: str = Query(default=None),
    degree_type: str = Query(default=None),
):
    if q:
        progs = search_programs(q, limit=50)
    else:
        progs = get_all_programs()

    if college:
        progs = [p for p in progs if p.get("college", "").lower() == college.lower()]
    if degree_type:
        progs = [p for p in progs if p.get("degree_type", "").lower() == degree_type.lower()]

    return [
        {
            "program_name": p["program_name"],
            "degree_type": p.get("degree_type", ""),
            "college": p.get("college", ""),
            "plan_codes": p.get("plan_codes", []),
            "campuses": p.get("campuses", []),
            "total_credits": p.get("total_credits"),
        }
        for p in progs
    ]


@app.get("/course/{code:path}")
def course_detail(code: str):
    course = get_course(code)
    if not course:
        raise HTTPException(status_code=404, detail=f"Course '{code}' not found")
    return course


@app.get("/calendar")
def get_calendar():
    data = load_calendar()
    if not data:
        raise HTTPException(status_code=503, detail="Calendar data not available. Run /calendar/refresh first.")
    return data


@app.get("/calendar/current")
def get_current_calendar():
    data = load_calendar()
    if not data:
        raise HTTPException(status_code=503, detail="Calendar data not available.")
    current_name = data.get("current_semester", "")
    current_sem = next(
        (s for s in data.get("semesters", []) if s["semester"] == current_name),
        None,
    )
    if not current_sem:
        raise HTTPException(status_code=404, detail=f"Current semester '{current_name}' not found in data.")
    return {
        "semester": current_name,
        "year": current_sem.get("year"),
        "events": current_sem.get("events", []),
        "footnotes": current_sem.get("footnotes", {}),
        "scraped_at": data.get("scraped_at"),
    }


@app.post("/calendar/refresh")
def refresh_calendar_endpoint(
    key: str = Query(default=None),
    x_admin_key: str | None = Header(default=None),
):
    """Re-scrape the PSU academic calendar. Key-gated: it hits PSU's servers."""
    _require_admin(key, x_admin_key)
    try:
        data = refresh_calendar()
        return {
            "message": "Calendar refreshed",
            "semesters": [s["semester"] for s in data["semesters"]],
            "current_semester": data["current_semester"],
            "scraped_at": data["scraped_at"],
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Scrape failed: {exc}")


# ── Gen-Ed explorer (optional auth — unauthenticated users can browse) ────────

@app.get("/gen-ed")
def gen_ed(
    major: str = Query(default=None),
    current_user: dict | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    resolved_major = major
    if not resolved_major and current_user:
        resolved_major = get_user_major(current_user["uid"], db=db)
    data = build_gen_ed_response(resolved_major)
    return data


# ── Prerequisite map (major-aware) ────────────────────────────────────────────

@app.get("/prereq-map")
def prereq_map(
    major: str = Query(default=None),
    current_user: dict | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    resolved_major = major
    if not resolved_major and current_user:
        resolved_major = get_user_major(current_user["uid"], db=db)
    if not resolved_major:
        return {"program_name": None, "courses": [], "found": False}
    data = build_prereq_map(resolved_major)
    if data is None:
        return {"program_name": resolved_major, "courses": [], "found": False}
    data["found"] = True
    return data


# ── Suggested academic plan (major-aware) ─────────────────────────────────────

@app.get("/suggested-plan")
def suggested_plan(
    major: str = Query(default=None),
    current_user: dict | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    resolved_major = major
    if not resolved_major and current_user:
        resolved_major = get_user_major(current_user["uid"], db=db)
    if not resolved_major:
        return {"program_name": None, "plans": [], "found": False}
    data = build_suggested_plan(resolved_major)
    if data is None:
        return {"program_name": resolved_major, "plans": [], "found": False}
    data["found"] = True
    return data


# ── User profile (settings page; user-initiated, NOT called on login) ────────

class ProfileUpdate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=120)


@app.get("/user/profile")
def get_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == current_user["uid"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "email": user.email,
        "display_name": user.display_name,
        "major": user.selected_major,
    }


@app.patch("/user/profile")
def update_profile(
    req: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == current_user["uid"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.display_name = req.display_name.strip()
    db.commit()
    return {"ok": True, "display_name": user.display_name}


# ── Access gate (pilot: app is closed; code is checked server-side) ──────────

class AccessRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=120)


@app.post("/access/verify")
def verify_access(req: AccessRequest):
    """Pilot access gate. The code lives in the ACCESS_CODE env var on Railway —
    never in the frontend bundle. Unset var = gate closed (fail safe)."""
    expected = os.getenv("ACCESS_CODE")
    if not expected:
        raise HTTPException(status_code=503, detail="Access not configured yet.")
    if req.code.strip() != expected:
        raise HTTPException(status_code=403, detail="That code isn't valid.")
    return {"ok": True}


# ── Waitlist (public; landing-page signups) ───────────────────────────────────

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


class WaitlistRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=320)
    major: Optional[str] = Field(default=None, max_length=500)
    referral: Optional[str] = Field(default=None, max_length=120)


@app.post("/waitlist")
def join_waitlist(req: WaitlistRequest, db: Session = Depends(get_db)):
    """Public signup from the landing page. Dedupes by email; returns the
    signer's position so the page can show 'You're #N'."""
    email = req.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="That doesn't look like a valid email.")

    existing = db.query(models.WaitlistEntry).filter(models.WaitlistEntry.email == email).first()
    if existing:
        position = (
            db.query(models.WaitlistEntry)
            .filter(models.WaitlistEntry.id <= existing.id)
            .count()
        )
        return {"ok": True, "already": True, "position": position}

    entry = models.WaitlistEntry(
        email=email,
        major=(req.major or "").strip()[:500] or None,
        referral=(req.referral or "").strip()[:120] or None,
    )
    db.add(entry)
    db.commit()
    position = db.query(models.WaitlistEntry).count()
    logger.info("waitlist | new signup #%d | referral=%r", position, entry.referral)
    return {"ok": True, "already": False, "position": position}


@app.get("/admin/waitlist")
def admin_waitlist(
    key: str = Query(default=None),
    x_admin_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Key-gated export of all signups (pick your first-100 cohort from this)."""
    _require_admin(key, x_admin_key)
    rows = (
        db.query(models.WaitlistEntry)
        .order_by(models.WaitlistEntry.id.asc())
        .all()
    )
    return {
        "total": len(rows),
        "entries": [
            {
                "position": i + 1,
                "email": r.email,
                "major": r.major,
                "referral": r.referral,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "invited_at": r.invited_at.isoformat() if r.invited_at else None,
            }
            for i, r in enumerate(rows)
        ],
    }


# ── Admin: API cost dashboard (key-gated; not user-facing) ────────────────────

def _require_admin(key, x_admin_key):
    admin_key = os.getenv("ADMIN_KEY")
    if not admin_key:
        raise HTTPException(status_code=503, detail="Cost dashboard disabled: set ADMIN_KEY.")
    if (x_admin_key or key) != admin_key:
        raise HTTPException(status_code=403, detail="Invalid admin key.")


@app.get("/admin/review")
def admin_review(
    days: int = Query(default=7, ge=1, le=90),
    key: str = Query(default=None),
    x_admin_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """The weekly review: what students asked, what they rated down, what landed
    ungrounded. Key-gated — these are real student questions."""
    _require_admin(key, x_admin_key)
    return review_summary(db, days=days)


@app.get("/admin/costs")
def admin_costs(
    key: str = Query(default=None),
    x_admin_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Live OpenAI spend: totals (all-time / 30d / 24h), per feature+model,
    avg cost per chat, and a projected monthly figure."""
    _require_admin(key, x_admin_key)
    from backend.services.cost_service import summarize
    return summarize(db)


@app.get("/admin/costs/estimate")
def admin_cost_estimate(
    users: int = Query(...),
    msgs_per_user: float = Query(..., description="messages per user per month"),
    avg_input_tokens: int = Query(default=3000),
    avg_output_tokens: int = Query(default=450),
    key: str = Query(default=None),
    x_admin_key: str | None = Header(default=None),
):
    """What-if projection from usage assumptions (no recorded data needed)."""
    _require_admin(key, x_admin_key)
    from backend.services.cost_service import estimate
    return estimate(users, msgs_per_user, avg_input_tokens, avg_output_tokens)


# ── Auth-required endpoints ───────────────────────────────────────────────────

@app.post("/auth/sync")
def sync_user(
    current_user: dict = Depends(get_current_user_any),
    db: Session = Depends(get_db),
):
    """Called after login to upsert user record. Returns the user's persisted
    state (major, doc presence) so the frontend can hydrate without a second
    round-trip and without racing against this insert."""
    uid = current_user["uid"]
    # Clerk JWTs only carry `sub`; fetch email/name from the Clerk user API.
    # Don't fail the sync if Clerk is briefly unreachable — log and proceed
    # with whatever we already have (or just the uid on first sign-in).
    try:
        details = fetch_user_details(uid)
    except Exception as exc:
        logger.warning("Clerk user fetch failed for uid=%r: %s", uid, exc)
        details = {"email": None, "name": None}

    user = db.query(models.User).filter_by(id=uid).first()
    if not user:
        user = models.User(
            id=uid,
            email=details.get("email"),
            display_name=details.get("name"),
        )
        db.add(user)
    else:
        if details.get("email"):
            user.email = details["email"]
        if details.get("name"):
            user.display_name = details["name"]
        user.last_login = datetime.now(timezone.utc)
    db.commit()
    return {
        "message": "User synced",
        "uid": uid,
        "major": user.selected_major,
        "has_doc": has_student_doc(uid, db=db),
    }


@app.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["uid"]
    check_chat_rate_limit(user_id)
    logger.info("chat/stream | question=%r | history_turns=%d | user_id=%r", req.question[:80], len(req.history), user_id)
    history = [{"role": m.role, "content": m.content} for m in req.history]
    return StreamingResponse(
        ask_advisor_stream(
            req.question,
            history=history,
            user_id=user_id,
            conversation_id=req.conversation_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/messages/{message_id}/rating")
def rate_message(
    message_id: int,
    req: RatingRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Thumbs up/down on an answer. Scoped to the caller's own conversations."""
    ok = set_rating(db, message_id, req.rating, current_user["uid"])
    if not ok:
        raise HTTPException(status_code=404, detail="Message not found.")
    return {"ok": True}


@app.get("/dashboard")
def get_dashboard(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user["uid"]

    if not has_student_doc(user_id, db=db):
        return {"available": False, "message": "No student document uploaded"}

    doc = get_current_student_doc(user_id, db=db)
    audit_parse = doc.get("audit_parse") or {}
    doc_type = doc.get("doc_type") or "academic_document"

    # ── Credits ──────────────────────────────────────────────────────────
    overall_totals = audit_parse.get("overall_totals", {})
    credits_required = 0.0
    credits_used = 0.0
    credits_needed = 0.0

    for vals in overall_totals.values():
        if vals.get("required", 0) > credits_required:
            credits_required = vals["required"]
            credits_used = vals.get("used", 0)
            credits_needed = vals.get("needed", 0)

    degree_progress_pct = round((credits_used / credits_required * 100), 1) if credits_required > 0 else 0

    # ── Status ────────────────────────────────────────────────────────────
    if degree_progress_pct >= 75:
        status = "On Track"
    elif degree_progress_pct >= 40:
        status = "In Progress"
    else:
        status = "Early Stage"

    # ── Remaining requirements ─────────────────────────────────────────
    import re as _re
    unsatisfied_blocks = audit_parse.get("unsatisfied_blocks", [])
    remaining_requirements = []
    or_group_seen = False
    seen_titles = set()

    for block in unsatisfied_blocks:
        title = (block.get("title") or "Unknown Requirement").strip()
        if title in seen_titles:
            continue
        seen_titles.add(title)

        units = block.get("units", {})

        if _re.match(r'^\*?OR\*?\s*Group\s+\d+|^Group\s+\d+$', title, _re.IGNORECASE):
            if not or_group_seen:
                or_group_seen = True
                remaining_requirements.append({
                    "title": "Upper-Level Electives (complete one group in consultation with your advisor)",
                    "credits_needed": units.get("needed", 6.0),
                    "credits_required": units.get("required", 6.0),
                    "courses": [],
                })
            continue

        remaining_requirements.append({
            "title": title,
            "credits_needed": units.get("needed", 0),
            "credits_required": units.get("required", 0),
            "courses": block.get("course_list", []),
        })

    # ── Recommended next semester ──────────────────────────────────────
    in_progress = audit_parse.get("in_progress_courses", [])
    remaining_required = audit_parse.get("remaining_required_courses", [])
    recommended = remaining_required[:5]
    if not recommended:
        for block in unsatisfied_blocks:
            if block.get("course_list"):
                recommended = block["course_list"][:5]
                break

    # ── Alerts ─────────────────────────────────────────────────────────
    alerts = []
    if doc_type == "what_if_report":
        alerts.append({
            "type": "warning",
            "message": "This data is from a What-If Report. Run a Degree Audit on LionPATH for official accuracy.",
        })
    if in_progress:
        alerts.append({
            "type": "info",
            "message": f"{len(in_progress)} course(s) currently in progress: {', '.join(in_progress[:4])}.",
        })
    if 0 < credits_needed <= 30:
        alerts.append({
            "type": "success",
            "message": f"You're close! Only {credits_needed:.0f} credits remaining to graduate.",
        })

    return {
        "available": True,
        "doc_type": doc_type,
        "advisor": audit_parse.get("advisor"),
        "credits_completed": credits_used,
        "credits_remaining": credits_needed,
        "credits_required": credits_required,
        "degree_progress_pct": degree_progress_pct,
        "status": status,
        "remaining_requirements": remaining_requirements,
        "in_progress_courses": in_progress,
        "recommended_next_semester": recommended,
        "alerts": alerts,
        # Normalized progress for the frontend tool views (Checklist, Gen Ed,
        # Prereq Map, GPA Calc) so they react to the uploaded audit instead of
        # being manual-only.
        "progress": {
            "completed_courses": [c["code"] for c in audit_parse.get("completed_courses", [])],
            "in_progress_courses": in_progress,
            "remaining_courses": remaining_required,
            "cumulative_gpa": audit_parse.get("cumulative_gpa"),
            "earned_credits": audit_parse.get("earned_credits", 0.0),
        },
    }


@app.post("/user/major")
def set_major(
    req: MajorRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    set_user_major(current_user["uid"], req.major, db=db)
    logger.info("set_major | user_id=%r major=%r", current_user["uid"], req.major)
    return {"message": "Major saved", "major": req.major}


@app.post("/clear-student-doc")
def clear_student_doc(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user["uid"]
    logger.info("Student document cleared | user_id=%r", user_id)
    clear_student_document(user_id, db=db)
    return {"message": "Student document cleared"}


@app.post("/upload-student-doc")
async def upload_student_doc(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user["uid"]
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    logger.info("upload-student-doc | filename=%r | user_id=%r", file.filename, user_id)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    doc_info = load_student_document(file_path, file.filename, user_id, db=db)
    logger.info("upload-student-doc | doc_type=%r", doc_info.get("doc_type"))

    deleted = cleanup_upload_dir()
    if deleted:
        logger.info("upload-student-doc | cleanup removed %d old file(s)", deleted)

    return {
        "message": "File uploaded successfully",
        "filename": file.filename,
        "path": file_path,
        "doc_type": doc_info.get("doc_type"),
        "detected_major": doc_info.get("detected_major"),
    }
