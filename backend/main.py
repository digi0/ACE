import logging
import os
from datetime import datetime, timezone

from fastapi import FastAPI, Query, Form, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.config import UPLOAD_DIR, LOG_LEVEL
from backend.database import engine, Base, get_db
from backend import models  # noqa: F401 — registers models with Base
from backend.firebase_auth import get_current_user, get_optional_user, get_current_user_any
from backend.services.vault_service import get_all_vault_records, search_vault
from backend.services.chat_service import ask_advisor, ask_advisor_stream
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

# ── CORS ──────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:8000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
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


class MajorRequest(BaseModel):
    major: str = Field(..., min_length=1, max_length=500)


# ── Public endpoints ──────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "PSU Academic Advisor Backend Running"}


@app.get("/vault")
def get_vault_records():
    records = get_all_vault_records()
    return {"total_records": len(records), "data": records}


@app.get("/vault/search")
def search_vault_records(
    category: str = Query(default=None),
    used_for: str = Query(default=None),
    keyword: str = Query(default=None)
):
    results = search_vault(category=category, used_for=used_for, keyword=keyword)
    return {"total_results": len(results), "data": results}


@app.get("/chat")
def chat_with_advisor(question: str = Query(...)):
    return ask_advisor(question)


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
def refresh_calendar_endpoint():
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


# ── Auth-required endpoints ───────────────────────────────────────────────────

@app.post("/auth/sync")
def sync_user(
    current_user: dict = Depends(get_current_user_any),
    db: Session = Depends(get_db),
):
    """Called after login to upsert user record in the database."""
    user = db.query(models.User).filter_by(id=current_user["uid"]).first()
    if not user:
        user = models.User(
            id=current_user["uid"],
            email=current_user.get("email"),
            display_name=current_user.get("name"),
        )
        db.add(user)
    else:
        user.email = current_user.get("email", user.email)
        user.display_name = current_user.get("name", user.display_name)
        user.last_login = datetime.now(timezone.utc)
    db.commit()
    return {"message": "User synced", "uid": current_user["uid"]}


@app.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["uid"]
    logger.info("chat/stream | question=%r | history_turns=%d | user_id=%r", req.question[:80], len(req.history), user_id)
    history = [{"role": m.role, "content": m.content} for m in req.history]
    return StreamingResponse(
        ask_advisor_stream(req.question, history=history, user_id=user_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
                    "title": "400-Level Non-CMPSC/CMPEN Electives (complete one 6-cr group with advisor)",
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


@app.get("/user/major")
def get_major(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    major = get_user_major(current_user["uid"], db=db)
    return {"major": major}


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
