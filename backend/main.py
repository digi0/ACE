import logging
import os

from fastapi import FastAPI, Query, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List

from backend.config import UPLOAD_DIR, LOG_LEVEL
from backend.services.vault_service import get_all_vault_records, search_vault
from backend.services.chat_service import ask_advisor, ask_advisor_stream
from backend.services.student_doc_service import (
    load_student_document,
    clear_student_document,
    get_current_student_doc,
    has_student_doc,
    cleanup_upload_dir,
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI()


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=8000)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    history: List[ChatMessage] = Field(default_factory=list)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
def root():
    return {"message": "PSU Academic Advisor Backend Running"}


@app.get("/vault")
def get_vault_records():
    records = get_all_vault_records()
    return {
        "total_records": len(records),
        "data": records
    }


@app.get("/vault/search")
def search_vault_records(
    category: str = Query(default=None),
    used_for: str = Query(default=None),
    keyword: str = Query(default=None)
):
    results = search_vault(category=category, used_for=used_for, keyword=keyword)
    return {
        "total_results": len(results),
        "data": results
    }


@app.get("/chat")
def chat_with_advisor(question: str = Query(...)):
    return ask_advisor(question)


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    logger.info("chat/stream | question=%r | history_turns=%d", req.question[:80], len(req.history))
    history = [{"role": m.role, "content": m.content} for m in req.history]
    return StreamingResponse(
        ask_advisor_stream(req.question, history=history),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/dashboard")
def get_dashboard():
    if not has_student_doc():
        return {"available": False, "message": "No student document uploaded"}

    doc = get_current_student_doc()
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

        # Collapse *OR* Group 1–N blocks into one descriptive entry
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


@app.post("/clear-student-doc")
def clear_student_doc():
    logger.info("Student document cleared")
    clear_student_document()
    return {"message": "Student document cleared"}


@app.post("/upload-student-doc")
async def upload_student_doc(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    logger.info("upload-student-doc | filename=%r", file.filename)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    doc_info = load_student_document(file_path, file.filename)
    logger.info("upload-student-doc | doc_type=%r", doc_info.get("doc_type"))

    deleted = cleanup_upload_dir()
    if deleted:
        logger.info("upload-student-doc | cleanup removed %d old file(s)", deleted)

    return {
        "message": "File uploaded successfully",
        "filename": file.filename,
        "path": file_path,
        "doc_type": doc_info.get("doc_type"),
    }