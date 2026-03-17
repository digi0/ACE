import os
import re
import logging
from pypdf import PdfReader
from backend.services.audit_parser_service import parse_whatif_blocks
from backend.config import UPLOAD_DIR, MAX_UPLOAD_FILES

_logger = logging.getLogger(__name__)


def cleanup_upload_dir() -> int:
    """Delete the oldest files in UPLOAD_DIR when the count exceeds MAX_UPLOAD_FILES.

    Returns the number of files deleted.
    """
    try:
        entries = [
            os.path.join(UPLOAD_DIR, f)
            for f in os.listdir(UPLOAD_DIR)
            if os.path.isfile(os.path.join(UPLOAD_DIR, f))
        ]
        if len(entries) <= MAX_UPLOAD_FILES:
            return 0

        # Sort oldest-first by last-modified time
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

_current_student_doc = {
    "filename": None,
    "file_path": None,
    "doc_type": None,
    "text": None,
    "analysis": None,
    "audit_parse": None,
}


def extract_pdf_text(pdf_path):
    reader = PdfReader(pdf_path)
    full_text = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            cleaned = text.strip()
            if cleaned:
                full_text.append(cleaned)

    return "\n".join(full_text)


def detect_doc_type(filename, text):
    combined = f"{filename}\n{text}".lower()

    if "what-if" in combined or "what if" in combined:
        return "what_if_report"

    if "degree audit" in combined or "academic requirements report" in combined:
        return "degree_audit"

    if "transcript" in combined:
        return "transcript"

    return "academic_document"


def normalize_line(line):
    return " ".join(line.split()).strip()


def looks_like_course(line):
    return bool(re.search(r"\b[A-Z]{2,6}\s?\d{3}[A-Z]?\b", line.upper()))


def extract_course_code(line):
    match = re.search(r"\b([A-Z]{2,6}\s?\d{3}[A-Z]?)\b", line.upper())
    return match.group(1).strip() if match else None


def analyze_student_document(text):
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
            entry = {"course": code, "line": line}
            key = ("in_progress", line)
            if key not in seen:
                seen.add(key)
                analysis["in_progress_courses"].append(entry)
                analysis["all_flagged_lines"].append(line)

        if (
            ("WITHDRAW" in upper or "LATE DROP" in upper or "NOT SATISFACTORY" in upper or "UNSATISFACTORY" in upper)
            and looks_like_course(line)
        ):
            code = extract_course_code(line)
            entry = {"course": code, "line": line}
            key = ("withdrawn", line)
            if key not in seen:
                seen.add(key)
                analysis["withdrawn_or_unsat_courses"].append(entry)
                analysis["all_flagged_lines"].append(line)

        unsat_phrases = [
            "UNSATISFIED",
            "NOT SATISFIED",
            "STILL NEEDED",
            "NEEDS",
            "REMAINING",
            "INCOMPLETE",
            "NOT COMPLETE",
        ]

        if any(phrase in upper for phrase in unsat_phrases):
            key = ("unsat", line)
            if key not in seen:
                seen.add(key)
                analysis["unsatisfied_requirement_lines"].append(line)
                analysis["all_flagged_lines"].append(line)

            if "ELECTIVE" in upper:
                analysis["possible_remaining_electives"].append(line)

            if (
                "GENERAL EDUCATION" in upper
                or "GEN ED" in upper
                or "GENED" in upper
                or "GHW" in upper
                or "GQ" in upper
                or "GA" in upper
                or "GS" in upper
                or "GN" in upper
                or "US" in upper
                or "IL" in upper
            ):
                analysis["possible_remaining_geneds"].append(line)

    return analysis


def load_student_document(file_path, filename):
    extension = os.path.splitext(filename)[1].lower()

    if extension == ".pdf":
        text = extract_pdf_text(file_path)
    else:
        text = ""

    doc_type = detect_doc_type(filename, text)
    analysis = analyze_student_document(text)
    audit_parse = parse_whatif_blocks(text)

    _current_student_doc["filename"] = filename
    _current_student_doc["file_path"] = file_path
    _current_student_doc["doc_type"] = doc_type
    _current_student_doc["text"] = text
    _current_student_doc["analysis"] = analysis
    _current_student_doc["audit_parse"] = audit_parse

    return _current_student_doc.copy()


def get_current_student_doc():
    return _current_student_doc.copy()


def clear_student_document():
    for key in _current_student_doc:
        _current_student_doc[key] = None


def has_student_doc():
    return bool(_current_student_doc.get("text"))


def build_student_doc_context(max_chars=5000):
    text = _current_student_doc.get("text") or ""
    doc_type = _current_student_doc.get("doc_type") or "academic_document"
    filename = _current_student_doc.get("filename") or "unknown"
    analysis = _current_student_doc.get("analysis") or {}
    audit_parse = _current_student_doc.get("audit_parse") or {}

    if not text:
        return ""

    trimmed_text = text[:max_chars]

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
        f"Document content excerpt:\n{trimmed_text}"
    )