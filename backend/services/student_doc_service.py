import os
import re
import json
import logging
from datetime import datetime, timezone
from pypdf import PdfReader
from backend.services.audit_parser_service import parse_whatif_blocks
from backend.config import UPLOAD_DIR, MAX_UPLOAD_FILES
from backend.database import SessionLocal
from backend.models import User, UserDocument

_logger = logging.getLogger(__name__)


# ── DB session helper ──────────────────────────────────────────────────────

def _ensure_db(db):
    """Return (session, should_close). If db is None, opens a new one."""
    if db is not None:
        return db, False
    return SessionLocal(), True


def _ensure_user(db, user_id: str) -> User:
    """Get or create the User row for user_id (upsert by PK)."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        user = User(id=user_id)
        db.add(user)
        db.flush()
    return user


# ── Upload directory helpers ───────────────────────────────────────────────

def cleanup_upload_dir() -> int:
    """Delete oldest files in UPLOAD_DIR when count exceeds MAX_UPLOAD_FILES."""
    try:
        entries = [
            os.path.join(UPLOAD_DIR, f)
            for f in os.listdir(UPLOAD_DIR)
            if os.path.isfile(os.path.join(UPLOAD_DIR, f))
        ]
        if len(entries) <= MAX_UPLOAD_FILES:
            return 0
        entries.sort(key=lambda p: os.path.getmtime(p))
        to_delete = entries[: len(entries) - MAX_UPLOAD_FILES]
        for path in to_delete:
            try:
                os.remove(path)
                _logger.info("cleanup_upload_dir | deleted %r", path)
            except OSError as exc:
                _logger.warning("cleanup_upload_dir | could not delete %r: %s", path, exc)
        return len(to_delete)
    except Exception as exc:
        _logger.warning("cleanup_upload_dir | error: %s", exc)
        return 0


# ── PDF helpers ────────────────────────────────────────────────────────────

def extract_pdf_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            cleaned = text.strip()
            if cleaned:
                pages.append(cleaned)
    return "\n".join(pages)


def detect_doc_type(filename: str, text: str) -> str:
    combined = f"{filename}\n{text}".lower()
    if "what-if" in combined or "what if" in combined:
        return "what_if_report"
    if "degree audit" in combined or "academic requirements report" in combined:
        return "degree_audit"
    if "transcript" in combined:
        return "transcript"
    return "academic_document"


def normalize_line(line: str) -> str:
    return " ".join(line.split()).strip()


def looks_like_course(line: str) -> bool:
    return bool(re.search(r"\b[A-Z]{2,6}\s?\d{3}[A-Z]?\b", line.upper()))


def extract_course_code(line: str):
    match = re.search(r"\b([A-Z]{2,6}\s?\d{3}[A-Z]?)\b", line.upper())
    return match.group(1).strip() if match else None


def analyze_student_document(text: str) -> dict:
    lines = [normalize_line(line) for line in text.splitlines() if normalize_line(line)]
    analysis = {
        "in_progress_courses": [],
        "withdrawn_or_unsat_courses": [],
        "unsatisfied_requirement_lines": [],
        "possible_remaining_electives": [],
        "possible_remaining_geneds": [],
        "all_flagged_lines": [],
    }
    seen = set()

    for line in lines:
        upper = line.upper()

        if "IN PROGRESS" in upper and looks_like_course(line):
            code = extract_course_code(line)
            key = ("in_progress", line)
            if key not in seen:
                seen.add(key)
                analysis["in_progress_courses"].append({"course": code, "line": line})
                analysis["all_flagged_lines"].append(line)

        if (
            ("WITHDRAW" in upper or "LATE DROP" in upper or "NOT SATISFACTORY" in upper or "UNSATISFACTORY" in upper)
            and looks_like_course(line)
        ):
            code = extract_course_code(line)
            key = ("withdrawn", line)
            if key not in seen:
                seen.add(key)
                analysis["withdrawn_or_unsat_courses"].append({"course": code, "line": line})
                analysis["all_flagged_lines"].append(line)

        unsat_phrases = [
            "UNSATISFIED", "NOT SATISFIED", "STILL NEEDED",
            "NEEDS", "REMAINING", "INCOMPLETE", "NOT COMPLETE",
        ]
        if any(phrase in upper for phrase in unsat_phrases):
            key = ("unsat", line)
            if key not in seen:
                seen.add(key)
                analysis["unsatisfied_requirement_lines"].append(line)
                analysis["all_flagged_lines"].append(line)
            if "ELECTIVE" in upper:
                analysis["possible_remaining_electives"].append(line)
            if any(tag in upper for tag in [
                "GENERAL EDUCATION", "GEN ED", "GENED",
                "GHW", "GQ", "GA", "GS", "GN", "US", "IL",
            ]):
                analysis["possible_remaining_geneds"].append(line)

    return analysis


# ── Per-user document store ────────────────────────────────────────────────

def load_student_document(file_path: str, filename: str, user_id: str, db=None) -> dict:
    extension = os.path.splitext(filename)[1].lower()
    text = extract_pdf_text(file_path) if extension == ".pdf" else ""

    doc_type = detect_doc_type(filename, text)
    analysis = analyze_student_document(text)
    audit_parse = parse_whatif_blocks(text)

    db, should_close = _ensure_db(db)
    try:
        _ensure_user(db, user_id)

        # Upsert: replace any existing doc for this user
        existing = db.query(UserDocument).filter_by(user_id=user_id).first()
        if existing:
            existing.filename = filename
            existing.doc_type = doc_type
            existing.text = text
            existing.analysis_json = json.dumps(analysis)
            existing.audit_parse_json = json.dumps(audit_parse)
            existing.uploaded_at = datetime.now(timezone.utc)
        else:
            doc = UserDocument(
                user_id=user_id,
                filename=filename,
                doc_type=doc_type,
                text=text,
                analysis_json=json.dumps(analysis),
                audit_parse_json=json.dumps(audit_parse),
            )
            db.add(doc)

        db.commit()
    finally:
        if should_close:
            db.close()

    # Auto-detect major from document text if user hasn't already set one
    detected_major = None
    if text and not get_user_major(user_id):
        try:
            from backend.services.program_service import detect_major_from_text
            detected_major = detect_major_from_text(text)
            if detected_major:
                set_user_major(user_id, detected_major)
                _logger.info(
                    "load_student_document | auto-detected major=%r for user_id=%r",
                    detected_major, user_id,
                )
        except Exception as exc:
            _logger.warning("load_student_document | major auto-detection failed: %s", exc)

    return {
        "filename": filename,
        "file_path": file_path,
        "doc_type": doc_type,
        "text": text,
        "analysis": analysis,
        "audit_parse": audit_parse,
        "detected_major": detected_major,
    }


def get_current_student_doc(user_id: str, db=None) -> dict:
    db, should_close = _ensure_db(db)
    try:
        row = (
            db.query(UserDocument)
            .filter_by(user_id=user_id)
            .order_by(UserDocument.uploaded_at.desc())
            .first()
        )
    finally:
        if should_close:
            db.close()

    if not row:
        return {
            "filename": None, "file_path": None, "doc_type": None,
            "text": None, "analysis": None, "audit_parse": None,
        }

    return {
        "filename": row.filename,
        "file_path": None,
        "doc_type": row.doc_type,
        "text": row.text,
        "analysis": json.loads(row.analysis_json) if row.analysis_json else None,
        "audit_parse": json.loads(row.audit_parse_json) if row.audit_parse_json else None,
    }


def clear_student_document(user_id: str, db=None) -> None:
    db, should_close = _ensure_db(db)
    try:
        db.query(UserDocument).filter_by(user_id=user_id).delete()
        db.commit()
    finally:
        if should_close:
            db.close()


def has_student_doc(user_id: str, db=None) -> bool:
    db, should_close = _ensure_db(db)
    try:
        row = (
            db.query(UserDocument.id)
            .filter(
                UserDocument.user_id == user_id,
                UserDocument.text.isnot(None),
                UserDocument.text != "",
            )
            .first()
        )
        return row is not None
    finally:
        if should_close:
            db.close()


# ── Per-user major preferences ─────────────────────────────────────────────

def set_user_major(user_id: str, major: str, db=None) -> None:
    db, should_close = _ensure_db(db)
    try:
        user = _ensure_user(db, user_id)
        user.selected_major = major.strip()
        db.commit()
    finally:
        if should_close:
            db.close()


def get_user_major(user_id: str, db=None) -> str | None:
    if not user_id:
        return None
    db, should_close = _ensure_db(db)
    try:
        user = db.query(User).filter_by(id=user_id).first()
        return user.selected_major if user else None
    finally:
        if should_close:
            db.close()


def clear_user_major(user_id: str, db=None) -> None:
    db, should_close = _ensure_db(db)
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if user:
            user.selected_major = None
            db.commit()
    finally:
        if should_close:
            db.close()


def build_student_doc_context(user_id: str, max_chars: int = 5000) -> str:
    doc = get_current_student_doc(user_id)
    text = doc.get("text") or ""
    if not text:
        return ""

    doc_type = doc.get("doc_type") or "academic_document"
    filename = doc.get("filename") or "unknown"
    analysis = doc.get("analysis") or {}
    audit_parse = doc.get("audit_parse") or {}

    analysis_lines = []

    advisor = audit_parse.get("advisor")
    if advisor:
        analysis_lines.append(f"Student's personally assigned advisor: {advisor}")

    in_progress = analysis.get("in_progress_courses", [])
    withdrawn = analysis.get("withdrawn_or_unsat_courses", [])
    unsat = analysis.get("unsatisfied_requirement_lines", [])
    electives = analysis.get("possible_remaining_electives", [])
    geneds = analysis.get("possible_remaining_geneds", [])

    if in_progress:
        analysis_lines.append("In-progress courses detected:")
        for item in in_progress[:15]:
            analysis_lines.append(f"- {item['line']}")
    if withdrawn:
        analysis_lines.append("Withdrawn / not satisfactory courses detected:")
        for item in withdrawn[:15]:
            analysis_lines.append(f"- {item['line']}")
    if unsat:
        analysis_lines.append("Unsatisfied or remaining requirement lines detected:")
        for line in unsat[:20]:
            analysis_lines.append(f"- {line}")
    if electives:
        analysis_lines.append("Possible remaining elective-related lines:")
        for line in electives[:10]:
            analysis_lines.append(f"- {line}")
    if geneds:
        analysis_lines.append("Possible remaining gen ed-related lines:")
        for line in geneds[:10]:
            analysis_lines.append(f"- {line}")

    analysis_block = "\n".join(analysis_lines) if analysis_lines else "No structured findings detected."

    return (
        f"Student uploaded document type: {doc_type}\n"
        f"Filename: {filename}\n\n"
        f"Structured findings from the document:\n{analysis_block}\n\n"
        f"Document content excerpt:\n{text[:max_chars]}"
    )
