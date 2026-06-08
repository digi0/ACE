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
    """'CMPSC  465N' → 'CMPSC 465N' (tolerates None / non-str)."""
    return re.sub(r"\s+", " ", (code or "").strip().upper())


# Honors/section suffixes that denote a *variant* of the same course (MATH 141H
# is Calc II, honors). We collapse these to the base course in graphs so they
# don't appear as separate nodes. 'W' (writing) is intentionally excluded — a
# W-course is a distinct requirement, not a variant.
_VARIANT_SUFFIXES = set("ABEGHMST")


def _canonical_code(code: str) -> str:
    """Collapse a lettered course variant to its base when the base exists.

    'MATH 141H' → 'MATH 141' (base in catalog); 'CMPSC 431W' stays (W kept,
    and no base 'CMPSC 431'); codes with no trailing letter are unchanged.
    """
    c = _normalize_code(code)
    m = re.match(r"^([A-Z]{2,8} \d{1,3})([A-Z])$", c)
    if m and m.group(2) in _VARIANT_SUFFIXES and m.group(1) in _courses_by_code:
        return m.group(1)
    return c


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


# ── Major-aware Prerequisite Map ───────────────────────────────────────────────

_PREREQ_MAP_MAX_NODES = 40


def build_prereq_map(program_name: str) -> dict | None:
    """
    Build a dependency graph of a program's required courses for the Prereq Map
    tool. Nodes are the program's prescribed courses plus its choice-group
    options; edges are prerequisites that are themselves in the node set (so the
    graph stays self-contained, like the old hardcoded CMPSC map). Tier = the
    course's depth in the prerequisite chain (0-based depth + 1 for display).

    Returns None if the program is unknown.
    """
    prog = get_program(program_name)
    if not prog:
        return None

    reqs = prog.get("requirements", {})
    node_codes: list[str] = []
    kind_of: dict[str, str] = {}
    seen: set[str] = set()

    def _add(raw_code: str, kind: str) -> bool:
        c = _normalize_code(raw_code)
        if c and c not in seen:
            seen.add(c)
            node_codes.append(c)
            kind_of[c] = kind
            return True
        return False

    # Backbone: the program's prescribed (required) courses.
    for item in reqs.get("prescribed", []):
        if item.get("code"):
            _add(_canonical_code(item["code"]), "required")

    # Expand transitively through prerequisites that exist in the catalog, so
    # the dependency chain (e.g. CMPSC 121 → 122 → 221) is visible even when the
    # feeder courses are entrance-to-major rather than prescribed. Lettered
    # variants (MATH 141H) are collapsed to their base. Bounded by a node cap so
    # dense majors don't produce an unreadable graph.
    queue = list(node_codes)
    while queue and len(node_codes) < _PREREQ_MAP_MAX_NODES:
        course = _courses_by_code.get(queue.pop(0))
        if not course:
            continue
        for pr in course.get("prerequisites", []):
            pc = _canonical_code(pr.get("code", ""))
            if pc and pc in _courses_by_code and pc not in seen:
                if _add(pc, "prereq"):
                    queue.append(pc)
                if len(node_codes) >= _PREREQ_MAP_MAX_NODES:
                    break

    node_set = set(node_codes)

    # In-set prerequisites per course (collapsed to canonical, deduped)
    prereq_codes: dict[str, list[str]] = {}
    for code in node_codes:
        course = _courses_by_code.get(code)
        prs: list[str] = []
        if course:
            for pr in course.get("prerequisites", []):
                pc = _canonical_code(pr.get("code", ""))
                if pc in node_set and pc != code and pc not in prs:
                    prs.append(pc)
        prereq_codes[code] = prs

    # Tier = longest prerequisite chain depth (memoized, cycle-guarded)
    tier: dict[str, int] = {}

    def _depth(code: str, stack: frozenset) -> int:
        if code in tier:
            return tier[code]
        if code in stack:
            return 0  # defensive: prereq cycle
        prs = prereq_codes.get(code, [])
        d = 0 if not prs else 1 + max(_depth(p, stack | {code}) for p in prs)
        tier[code] = d
        return d

    for code in node_codes:
        _depth(code, frozenset())

    id_of = {c: c.replace(" ", "") for c in node_codes}
    nodes: list[dict] = []
    for code in node_codes:
        course = _courses_by_code.get(code)
        prs = prereq_codes[code]
        # Unlock mode. Require ALL prereqs only when the condition is a pure
        # conjunction ("X and Y"). Pure-OR or mixed AND/OR conditions → 'any',
        # so a set of alternative prereqs (e.g. the first-year-writing options
        # before ENGL 202C) never keeps a course permanently locked.
        mode = "all"
        if course and prs:
            prs_set = set(prs)
            conds = " ".join(
                p.get("condition", "")
                for p in course.get("prerequisites", [])
                if _canonical_code(p.get("code", "")) in prs_set
            ).lower()
            if not (" and " in conds and " or " not in conds):
                mode = "any"
        nodes.append({
            "id": id_of[code],
            "code": code,
            "name": (course or {}).get("title", ""),
            "credits": (course or {}).get("credits", ""),
            "tier": tier[code] + 1,
            "prereqs": [id_of[p] for p in prs],
            "prereqMode": mode,
            "kind": kind_of[code],
        })

    return {
        "program_name": prog["program_name"],
        "college": (prog.get("college", "") or "").replace("-", " "),
        "max_tier": max((n["tier"] for n in nodes), default=0),
        "courses": nodes,
    }


# ── Suggested Academic Plan ────────────────────────────────────────────────────

_YEAR_ORDINAL = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
}
_SEASON_ORDER = {"fall": 0, "winter": 1, "spring": 2, "summer": 3}


def _clean_text(s) -> str:
    return re.sub(r"\s+", " ", str(s).replace("\xa0", " ")).strip()


def _semester_label(key: str) -> str:
    """'first_year_fall' → 'Year 1 · Fall'."""
    parts = key.split("_")
    yr = _YEAR_ORDINAL.get(parts[0]) if parts else None
    season = parts[-1].capitalize() if parts else ""
    if yr and season:
        return f"Year {yr} · {season}"
    return key.replace("_", " ").title()


def _semester_sort_key(key: str) -> tuple:
    parts = key.split("_")
    return (_YEAR_ORDINAL.get(parts[0], 99), _SEASON_ORDER.get(parts[-1], 9))


def build_suggested_plan(program_name: str) -> dict | None:
    """
    Build the college's suggested semester-by-semester academic plan for a
    program, from programs.json `suggested_plan`. A program may have more than
    one plan variant (e.g. University Park vs Commonwealth campuses); all are
    returned. Returns None if the program is unknown.
    """
    prog = get_program(program_name)
    if not prog:
        return None

    raw = prog.get("suggested_plan") or {}
    plans: list[dict] = []
    for label, semesters in raw.items():
        if not isinstance(semesters, dict):
            continue
        sem_out: list[dict] = []
        for key, courses in sorted(semesters.items(), key=lambda kv: _semester_sort_key(kv[0])):
            cleaned: list[dict] = []
            total = 0.0
            for c in courses or []:
                cr = c.get("credits")
                if isinstance(cr, (int, float)):
                    total += cr
                cleaned.append({"description": _clean_text(c.get("description", "")), "credits": cr})
            sem_out.append({
                "key": key,
                "label": _semester_label(key),
                "courses": cleaned,
                "total_credits": round(total, 1),
            })
        plans.append({"label": _clean_text(label), "semesters": sem_out})

    return {
        "program_name": prog["program_name"],
        "total_credits": prog.get("total_credits"),
        "plans": plans,
    }
