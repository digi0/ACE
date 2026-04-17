"""
Program and course data service.

Loads programs.json and courses.json once at module import time and provides
fast in-memory lookups for the rest of the backend.  All public functions are
safe to call at import time; if the data files are missing the functions return
sensible empty results and log a warning.
"""

import json
import logging
import re
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"

# ── In-memory indexes ──────────────────────────────────────────────────────────
_programs: list[dict] = []
_courses_by_code: dict[str, dict] = {}        # "CMPSC 465"  → course dict
_programs_by_name: dict[str, dict] = {}       # lower name   → program dict
_programs_by_plan_code: dict[str, dict] = {}  # "CMPSC_BS"   → program dict
_courses_by_dept: dict[str, list] = {}        # "CMPSC"      → [course, ...]
_courses_by_gen_ed: dict[str, list] = {}      # "GQ"         → [course, ...]
_popular_courses: set[str] = set()            # codes appearing in 5+ programs


# ── Internal helpers ───────────────────────────────────────────────────────────

def _normalize_code(code: str) -> str:
    """'CMPSC  465N' → 'CMPSC 465N'"""
    return re.sub(r"\s+", " ", code.strip().upper())


def _load_data() -> None:
    global _programs

    programs_path = _DATA_DIR / "programs.json"
    courses_path  = _DATA_DIR / "courses.json"

    # ── Programs ──────────────────────────────────────────────────────────────
    if programs_path.exists():
        _programs = json.loads(programs_path.read_text(encoding="utf-8"))
        for prog in _programs:
            name = prog.get("program_name", "").strip()
            if name:
                _programs_by_name[name.lower()] = prog
            for pc in prog.get("plan_codes", []):
                if pc:
                    _programs_by_plan_code[pc.strip().upper()] = prog
        logger.info("program_service: loaded %d programs", len(_programs))
    else:
        logger.warning("program_service: programs.json not found at %s", programs_path)

    # ── Courses ───────────────────────────────────────────────────────────────
    if courses_path.exists():
        all_courses = json.loads(courses_path.read_text(encoding="utf-8"))
        for course in all_courses:
            # Normalize any leftover non-breaking spaces in prereq conditions
            for prereq in course.get("prerequisites", []):
                if prereq.get("condition"):
                    prereq["condition"] = prereq["condition"].replace("\xa0", " ")
                if prereq.get("code"):
                    prereq["code"] = prereq["code"].replace("\xa0", " ")
            code = _normalize_code(course.get("code", ""))
            if code:
                _courses_by_code[code] = course
            dept = course.get("department", "").strip().upper()
            if dept:
                _courses_by_dept.setdefault(dept, []).append(course)
            for cat in course.get("gen_ed", {}).get("categories", []):
                _courses_by_gen_ed.setdefault(cat, []).append(course)
        logger.info("program_service: loaded %d courses", len(_courses_by_code))
    else:
        logger.warning("program_service: courses.json not found at %s", courses_path)

    # ── Popularity index ──────────────────────────────────────────────────────
    code_freq: dict[str, int] = {}
    for prog in _programs:
        reqs = prog.get("requirements", {})
        for item in reqs.get("prescribed", []):
            c = item.get("code", "")
            if c:
                code_freq[c] = code_freq.get(c, 0) + 1
        for item in reqs.get("additional", []):
            for opt in item.get("options", []):
                c = opt.get("code", "")
                if c:
                    code_freq[c] = code_freq.get(c, 0) + 1
    threshold = 5
    _popular_courses.update(c for c, n in code_freq.items() if n >= threshold)
    logger.info(
        "program_service: %d popular courses (appears in %d+ programs)",
        len(_popular_courses), threshold,
    )


_load_data()


# ── Public lookup API ──────────────────────────────────────────────────────────

def get_all_programs() -> list[dict]:
    """Return list of all programs."""
    return _programs


def get_program(name: str) -> dict | None:
    """Exact case-insensitive lookup by program_name."""
    return _programs_by_name.get(name.strip().lower())


def get_program_by_plan_code(plan_code: str) -> dict | None:
    """Find program by plan code (e.g. 'CMPSC_BS')."""
    return _programs_by_plan_code.get(plan_code.strip().upper())


def search_programs(query: str, limit: int = 20) -> list[dict]:
    """Fuzzy search over program names. Substring matches scored higher."""
    q = query.strip().lower()
    if not q:
        return _programs[:limit]

    results: list[tuple[float, dict]] = []
    for prog in _programs:
        name = prog.get("program_name", "").lower()
        if q in name:
            score = 1.0 + len(q) / max(len(name), 1)
        else:
            score = SequenceMatcher(None, q, name).ratio()
        if score > 0.3:
            results.append((score, prog))

    results.sort(key=lambda x: -x[0])
    return [p for _, p in results[:limit]]


def get_programs_by_college(college: str) -> list[dict]:
    """Return programs for a college slug (e.g. 'engineering')."""
    c = college.strip().lower()
    return [p for p in _programs if p.get("college", "").lower() == c]


def get_course(code: str) -> dict | None:
    """Lookup a course by code; normalizes whitespace/case."""
    return _courses_by_code.get(_normalize_code(code))


def get_courses_by_department(dept: str) -> list[dict]:
    """Return all courses for a department code."""
    return _courses_by_dept.get(dept.strip().upper(), [])


def get_prerequisites(code: str) -> list[dict]:
    """Return the prerequisites list for a course."""
    course = get_course(code)
    return (course or {}).get("prerequisites", [])


def get_gen_ed_courses(category: str) -> list[dict]:
    """Return all courses carrying a gen-ed category code (e.g. 'GQ')."""
    return _courses_by_gen_ed.get(category.strip().upper(), [])


def _get_all_program_codes(program: dict) -> set[str]:
    """Collect all course codes referenced anywhere in a program."""
    codes: set[str] = set()
    reqs = program.get("requirements", {})
    for item in reqs.get("prescribed", []):
        c = item.get("code", "")
        if c:
            codes.add(_normalize_code(c))
    for item in reqs.get("additional", []):
        for opt in item.get("options", []):
            c = opt.get("code", "")
            if c:
                codes.add(_normalize_code(c))
    return codes


def get_double_dips(program_name: str) -> list[dict]:
    """
    Return courses in the program that also carry gen-ed categories.
    Each entry: {code, title, credits, gen_ed_categories, is_prescribed}.
    """
    prog = get_program(program_name)
    if not prog:
        return []

    reqs = prog.get("requirements", {})
    results: list[dict] = []
    seen: set[str] = set()

    for item in reqs.get("prescribed", []):
        raw = item.get("code", "")
        code = _normalize_code(raw) if raw else ""
        if not code or code in seen:
            continue
        seen.add(code)
        course = _courses_by_code.get(code)
        if course and course.get("gen_ed", {}).get("categories"):
            results.append({
                "code": code,
                "title": item.get("title") or course.get("title", ""),
                "credits": item.get("credits") or course.get("credits", ""),
                "gen_ed_categories": course["gen_ed"]["categories"],
                "is_prescribed": True,
            })

    for item in reqs.get("additional", []):
        for opt in item.get("options", []):
            raw = opt.get("code", "")
            code = _normalize_code(raw) if raw else ""
            if not code or code in seen:
                continue
            seen.add(code)
            course = _courses_by_code.get(code)
            if course and course.get("gen_ed", {}).get("categories"):
                results.append({
                    "code": code,
                    "title": opt.get("title") or course.get("title", ""),
                    "credits": opt.get("credits") or course.get("credits", ""),
                    "gen_ed_categories": course["gen_ed"]["categories"],
                    "is_prescribed": False,
                })

    return results


# ── Gen-Ed endpoint builder ────────────────────────────────────────────────────

_GEN_ED_CATEGORIES = [
    {"code": "FYW", "label": "First-Year Writing",           "credits_required": 3},
    {"code": "GQ",  "label": "Quantification",               "credits_required": 3},
    {"code": "GN",  "label": "Natural Sciences",             "credits_required": 6},
    {"code": "GA",  "label": "Arts",                         "credits_required": 3},
    {"code": "GH",  "label": "Humanities",                   "credits_required": 3},
    {"code": "GS",  "label": "Social & Behavioral Sciences", "credits_required": 3},
    {"code": "GHW", "label": "Health & Physical Activity",   "credits_required": 2},
    {"code": "US",  "label": "United States Cultures",       "credits_required": 3},
    {"code": "IL",  "label": "International Cultures",       "credits_required": 3},
    {"code": "GWS", "label": "Writing & Speaking",           "credits_required": 3},
]


def build_gen_ed_response(program_name: str | None) -> dict:
    """
    Build the payload for GET /gen-ed.
    For each gen-ed category: list courses (capped at 80), tagged with
    'major-req' if in the user's program or 'popular' if cross-program.
    """
    prog = get_program(program_name) if program_name else None
    prog_codes = _get_all_program_codes(prog) if prog else set()

    program_info = None
    if prog:
        program_info = {
            "name": prog["program_name"],
            "total_credits": prog.get("total_credits"),
            "gen_ed_credits": prog.get("gen_ed_credits"),
            "gen_ed_overlap": prog.get("gen_ed_overlap", {}),
            "gen_ed_overlap_note": prog.get("gen_ed_overlap_note", ""),
        }

    categories_out = []
    for cat_def in _GEN_ED_CATEGORIES:
        code = cat_def["code"]
        raw_courses = _courses_by_gen_ed.get(code, [])

        courses_out = []
        for course in raw_courses[:80]:
            ccode = _normalize_code(course.get("code", ""))
            tags: list[str] = []
            if ccode in prog_codes:
                tags.append("major-req")
            elif ccode in _popular_courses:
                tags.append("popular")

            courses_out.append({
                "code": ccode,
                "title": course.get("title", ""),
                "credits": course.get("credits", ""),
                "department": course.get("department", ""),
                "tags": tags,
            })

        # major-req first, popular second, rest alphabetical
        courses_out.sort(
            key=lambda c: (
                0 if "major-req" in c["tags"] else
                1 if "popular" in c["tags"] else 2,
                c["code"],
            )
        )

        overlap_credits = (prog.get("gen_ed_overlap", {}) or {}).get(code, 0) if prog else 0

        categories_out.append({
            "code": code,
            "label": cat_def["label"],
            "credits_required": cat_def["credits_required"],
            "overlap_credits": overlap_credits,
            "course_count": len(raw_courses),
            "courses": courses_out,
        })

    return {
        "program": program_info,
        "categories": categories_out,
    }


# ── Major auto-detection from document text ────────────────────────────────────

def detect_major_from_text(text: str) -> str | None:
    """
    Try to identify the student's program from degree audit / what-if text.
    Strategy 1: find plan codes like CMPSC_BS.
    Strategy 2: substring-match known program names.
    Returns program_name string or None.
    """
    # Strategy 1: plan code pattern
    for code in re.findall(r"\b([A-Z]{2,8}_[A-Z0-9]{2,4})\b", text.upper()):
        prog = _programs_by_plan_code.get(code)
        if prog:
            return prog["program_name"]

    # Strategy 2: program name substring (only names ≥12 chars to avoid noise)
    text_lower = text.lower()
    best: tuple[int, str] | None = None
    for name_lower, prog in _programs_by_name.items():
        if len(name_lower) >= 12 and name_lower in text_lower:
            if best is None or len(name_lower) > best[0]:
                best = (len(name_lower), prog["program_name"])

    return best[1] if best else None


# ── Program context snippet for chat ──────────────────────────────────────────

def build_program_context_snippet(program_name: str) -> str:
    """
    Return a concise text block describing the program's requirements,
    suitable for injection into the chat system prompt.
    """
    prog = get_program(program_name)
    if not prog:
        return ""

    lines: list[str] = [
        f"=== PROGRAM REQUIREMENTS: {prog['program_name']} ===",
        f"College: {prog.get('college', 'unknown')}",
        f"Total credits required: {prog.get('total_credits', 'unknown')}",
    ]

    overlap = prog.get("gen_ed_overlap", {})
    if overlap:
        overlap_str = ", ".join(f"{k}: {v} cr" for k, v in overlap.items())
        lines.append(f"Gen Ed overlap with major: {overlap_str}")
    if prog.get("gen_ed_overlap_note"):
        lines.append(prog["gen_ed_overlap_note"])

    reqs = prog.get("requirements", {})
    prescribed = reqs.get("prescribed", [])
    if prescribed:
        lines.append("")
        lines.append("Prescribed (required) courses — C or higher usually required:")
        for item in prescribed:
            grade = f" (min {item['min_grade']})" if item.get("min_grade") else ""
            lines.append(
                f"  - {item['code']}: {item.get('title','')}"
                f" ({item.get('credits','')} cr){grade}"
            )

    additional = reqs.get("additional", [])
    if additional:
        lines.append("")
        lines.append("Additional / elective requirements:")
        for item in additional[:6]:   # cap to avoid overly long prompts
            desc = item.get("description", item.get("type", ""))
            cr   = item.get("credits", "")
            opts = item.get("options", [])
            opt_str = (
                ", ".join(o.get("code", "") for o in opts[:6])
                + (" ..." if len(opts) > 6 else "")
            )
            lines.append(
                f"  - {desc} ({cr} cr)"
                + (f" — choose from: {opt_str}" if opt_str else "")
            )

    return "\n".join(lines)
