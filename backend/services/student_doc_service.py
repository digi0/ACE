import os
import re
import json
import sqlite3
import logging
from pypdf import PdfReader
from backend.services.audit_parser_service import parse_whatif_blocks
from backend.config import UPLOAD_DIR, MAX_UPLOAD_FILES

_logger = logging.getLogger(__name__)

# ── SQLite persistence ─────────────────────────────────────────────────────
# Each user's document is stored as a row keyed by their Firebase UID.
#
# PRODUCTION NOTE: Replace this SQLite file with a proper database
# (e.g. PostgreSQL on Railway via DATABASE_URL) when multi-instance or
# high-traffic deployment is needed. SQLite is fine for a single Railway
# instance but data will be lost if the volume is ephemeral.
_DB_PATH = os.path.join("backend", "data", "ace_users.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_docs (
            user_id          TEXT PRIMARY KEY,
            filename         TEXT,
            doc_type         TEXT,
            text             TEXT,
            analysis_json    TEXT,
            audit_parse_json TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_prefs (
            user_id        TEXT PRIMARY KEY,
            selected_major TEXT
        )
    """)
    conn.commit()
    return conn


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

def load_student_document(file_path: str, filename: str, user_id: str) -> dict:
    extension = os.path.splitext(filename)[1].lower()
    text = extract_pdf_text(file_path) if extension == ".pdf" else ""

    doc_type = detect_doc_type(filename, text)
    analysis = analyze_student_document(text)
    audit_parse = parse_whatif_blocks(text)

    with _get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO user_docs
                (user_id, filename, doc_type, text, analysis_json, audit_parse_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                filename,
                doc_type,
                text,
                json.dumps(analysis),
                json.dumps(audit_parse),
            ),
        )
        conn.commit()

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


def get_current_student_doc(user_id: str) -> dict:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT filename, doc_type, text, analysis_json, audit_parse_json "
            "FROM user_docs WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    if not row:
        return {
            "filename": None, "file_path": None, "doc_type": None,
            "text": None, "analysis": None, "audit_parse": None,
        }

    filename, doc_type, text, analysis_json, audit_parse_json = row
    return {
        "filename": filename,
        "file_path": None,
        "doc_type": doc_type,
        "text": text,
        "analysis": json.loads(analysis_json) if analysis_json else None,
        "audit_parse": json.loads(audit_parse_json) if audit_parse_json else None,
    }


def clear_student_document(user_id: str) -> None:
    with _get_conn() as conn:
        conn.execute("DELETE FROM user_docs WHERE user_id = ?", (user_id,))
        conn.commit()


def has_student_doc(user_id: str) -> bool:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM user_docs WHERE user_id = ? AND text IS NOT NULL AND text != ''",
            (user_id,),
        ).fetchone()
    return bool(row)


# ── Per-user major preferences ─────────────────────────────────────────────────

def set_user_major(user_id: str, major: str) -> None:
    """Store (or update) the student's selected major."""
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO user_prefs (user_id, selected_major) VALUES (?, ?)",
            (user_id, major.strip()),
        )
        conn.commit()


def get_user_major(user_id: str) -> str | None:
    """Return the stored major for a user, or None if not set."""
    if not user_id:
        return None
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT selected_major FROM user_prefs WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return row[0] if row else None


def clear_user_major(user_id: str) -> None:
    """Remove the stored major for a user."""
    with _get_conn() as conn:
        conn.execute("DELETE FROM user_prefs WHERE user_id = ?", (user_id,))
        conn.commit()


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
