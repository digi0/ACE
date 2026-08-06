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

# Generous: the largest programme in programs.json has well under this many
# requirement groups, so in practice nothing is dropped. It exists only so a
# malformed record cannot produce an unbounded prompt.
_MAX_REQUIREMENT_GROUPS = 40


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
        # NOT capped at 6 any more. That cap silently dropped the entire calculus
        # sequence — MATH 140, 141, 220, 230 — from Computer Science, because the
        # maths groups sit at positions 8-11. Retrieval used to paper over it for
        # CS/DS and nothing covered it for the other 747 majors. The prompt budget
        # freed by gating the handbook pays for the full list many times over.
        for item in additional[:_MAX_REQUIREMENT_GROUPS]:
            desc = item.get("description", item.get("type", ""))
            cr   = item.get("credits", "")
            opts = item.get("options", [])
            opt_str = (
                ", ".join(o.get("code", "") for o in opts[:8])
                + (" ..." if len(opts) > 8 else "")
            )
            lines.append(
                f"  - {desc} ({cr} cr)"
                + (f" — choose from: {opt_str}" if opt_str else "")
            )

    # For many programs the Bulletin's requirement table is partial — professional
    # sequences (Nursing is the clearest case) list only the supporting courses
    # there and put the major's own coursework in the suggested plan. Without
    # this, ACE answers "what do I take for my degree?" with no NURS course in
    # sight, which reads as authoritative and is wrong.
    known = {_normalize_code(i.get("code", "")) for i in prescribed}
    known |= {
        _normalize_code(o.get("code", ""))
        for i in additional for o in i.get("options", [])
    }
    plan_only = _plan_only_codes(prog, known)
    if plan_only:
        lines.append("")
        lines.append(
            "Also in the Bulletin's suggested academic plan for this program, but "
            "NOT itemised in the requirement table above (the table is partial for "
            "this program — these are still part of the degree):"
        )
        lines.append("  " + ", ".join(plan_only))
        lines.append(
            "When listing degree requirements, include these too and tell the "
            "student to confirm the full sequence on the Bulletin: "
            + (prog.get("url") or "https://bulletins.psu.edu/")
        )

    return "\n".join(lines)


def _codes_in_text(text: str) -> list[str]:
    """Real catalog course codes mentioned in a plan description.

    Plan entries are prose ("ENGL 15 or 30H", "General Education Course Level 2"),
    so the regex alone yields junk subjects — gate on the catalog.
    """
    out = []
    for raw in _CODE_RE.findall(str(text).replace("\xa0", " ").upper()):
        code = _normalize_code(raw)
        if code in _courses_by_code and code not in out:
            out.append(code)
    return out


def _unmet_prereqs(code: str, done: set) -> list[str]:
    """Prerequisites still standing between the student and this course.

    Alternatives matter: CMPSC 121 lists MATH 110 *or* MATH 140, so a student who
    took MATH 140 is eligible. Treating the list as a conjunction would tell them
    they are blocked by a course they never needed. _prereq_mode already knows
    how to read the condition — reuse it rather than re-deriving.
    """
    prereqs = [p for p in get_prerequisites(code) if p.get("code")]
    codes = [_canonical_code(p["code"]) for p in prereqs]
    if not codes:
        return []
    outstanding = [c for c in dict.fromkeys(codes) if c not in done]
    if not outstanding:
        return []
    # 'any' => one satisfied prerequisite unlocks the course.
    if _prereq_mode(get_course(code), set(codes)) == "any" and len(outstanding) < len(set(codes)):
        return []
    return outstanding


def build_recommendation_context(program_name: str, completed_codes=None) -> dict | None:
    """Work out where a student is in their plan and what comes next.

    This is what turns "what should I take next semester?" from a recital of the
    whole requirement table into an actual proposal. Returns None when the
    program has no suggested plan to reason from — the caller must then say so
    rather than inventing a schedule.

    `completed_codes` comes from the uploaded audit. With none, the position is
    the start of the plan, which is still the right answer for a new student.
    """
    prog = get_program(program_name)
    plans = (prog or {}).get("suggested_plan") or {}
    if not plans:
        return None

    label, semesters = next(iter(plans.items()))
    if not isinstance(semesters, dict):
        return None

    done = {_canonical_code(c) for c in (completed_codes or [])}
    ordered = sorted(semesters.items(), key=lambda kv: _semester_sort_key(kv[0]))

    laid_out = []
    for key, entries in ordered:
        courses = []
        for entry in entries or []:
            # One plan entry is one SLOT in the schedule. When its description
            # names several courses ("ENGL 15 or ESL 15") they are alternatives
            # for that single slot, not four separate courses to take — flatten
            # them and the proposal tells a student to take all four.
            codes = _codes_in_text(entry.get("description", ""))
            if not codes:
                continue
            primary = codes[0]
            courses.append({
                "code": primary,
                "alternatives": codes[1:],
                "title": (_courses_by_code.get(primary) or {}).get("title", ""),
                "credits": entry.get("credits"),
                "done": any(_canonical_code(c) in done for c in codes),
            })
        laid_out.append({"semester": key, "courses": courses})

    # Where the student is: the earliest semester still carrying unfinished work.
    # ponytail: positional heuristic, not a degree solver. A student on an
    # alternative track (CMPSC 131/132 instead of 121/122) reads as "still in
    # first-year fall" because the plan's courses are genuinely untaken. The
    # proposal is still sound — those courses really are outstanding — but if
    # equivalences start mattering, resolve them against the audit's satisfied
    # requirement blocks instead of raw course codes.
    position, remaining = None, []
    for sem in laid_out:
        outstanding = [c for c in sem["courses"] if not c["done"]]
        if outstanding:
            position, remaining = sem["semester"], outstanding
            break
    if position is None:  # every plan course is done
        return {"plan_label": label, "position": None, "propose": [], "complete": True}

    # A semester that's nearly finished leaves too little to propose, so top up
    # from the next one rather than handing back a one-course "schedule".
    propose = list(remaining)
    if len(propose) < 3:
        idx = [s["semester"] for s in laid_out].index(position)
        for sem in laid_out[idx + 1:]:
            propose += [c for c in sem["courses"] if not c["done"]]
            if len(propose) >= 4:
                break

    for course in propose[:6]:
        course["unmet_prereqs"] = _unmet_prereqs(course["code"], done)

    return {
        "plan_label": label,
        "position": position,
        "propose": propose[:6],
        "complete": False,
        "personalised": bool(done),
    }


_PLAN_ONLY_LIMIT = 30


def _plan_only_codes(prog: dict, known: set[str]) -> list[str]:
    """Course codes in the suggested plan that the requirement table never names.

    Returns them in plan order (roughly semester order), capped so a long plan
    can't crowd the prompt.
    """
    found: list[str] = []
    seen = set(known)
    for option in (prog.get("suggested_plan") or {}).values():
        if not isinstance(option, dict):
            continue
        for semester in option.values():
            for entry in semester or []:
                text = str(entry.get("description", "")).replace("\xa0", " ").upper()
                for raw in _CODE_RE.findall(text):
                    code = _normalize_code(raw)
                    # Plan descriptions are prose ("ENGL 15 or 30H", "Elective 1",
                    # "General Education Course Level 2"), so the code regex alone
                    # yields junk subjects. Only real catalog courses survive.
                    if code in seen or code not in _courses_by_code:
                        continue
                    seen.add(code)
                    found.append(code)
                    if len(found) >= _PLAN_ONLY_LIMIT:
                        return found
    return found


# ── Major-aware Prerequisite Map ───────────────────────────────────────────────

_PREREQ_MAP_MAX_NODES = 60
_CODE_RE = re.compile(r"[A-Z]{2,8}\s*\d{1,3}[A-Z]?")


def _prereq_mode(course: dict | None, prereq_set: set) -> str:
    """'all' only when the prereq condition is a pure conjunction, else 'any'.

    Keeps alternative prereqs (X or Y) from permanently locking a course.
    """
    if not (course and prereq_set):
        return "all"
    conds = " ".join(
        p.get("condition", "")
        for p in course.get("prerequisites", [])
        if _canonical_code(p.get("code", "")) in prereq_set
    ).lower()
    return "all" if (" and " in conds and " or " not in conds) else "any"


def _extract_catalog_codes(text: str) -> list[str]:
    """Course codes in `text` that exist in the catalog, canonicalized, in order."""
    out: list[str] = []
    for m in _CODE_RE.finditer(_clean_text(text).upper()):
        c = _canonical_code(m.group(0))
        if c in _courses_by_code and c not in out:
            out.append(c)
    return out


def _build_map_nodes(node_tiers: dict[str, int], kind_of: dict[str, str]) -> list[dict]:
    """Build node dicts (with in-set prerequisite edges) from {code: tier}."""
    node_set = set(node_tiers)
    id_of = {c: c.replace(" ", "") for c in node_tiers}
    nodes: list[dict] = []
    for code, t in node_tiers.items():
        course = _courses_by_code.get(code)
        prs: list[str] = []
        if course:
            for pr in course.get("prerequisites", []):
                pc = _canonical_code(pr.get("code", ""))
                if pc in node_set and pc != code and pc not in prs:
                    prs.append(pc)
        nodes.append({
            "id": id_of[code],
            "code": code,
            "name": (course or {}).get("title", ""),
            "credits": (course or {}).get("credits", ""),
            "tier": t,
            "prereqs": [id_of[p] for p in prs],
            "prereqMode": _prereq_mode(course, set(prs)),
            "kind": kind_of.get(code, "course"),
        })
    return nodes


def build_prereq_map(program_name: str) -> dict | None:
    """
    Build a course dependency graph for ANY major, two ways:

    1. PLAN-DRIVEN (preferred) — read the college's suggested academic plan,
       place each real course at its plan semester (tier), and draw prerequisite
       edges between plan courses from courses.json. This gives a term-by-term
       map that matches what the department actually publishes.
    2. REQUIREMENTS fallback — for majors with no suggested plan, use the
       prescribed courses + their transitive prerequisites, tiered by
       prerequisite depth.

    Returns None only if the program is unknown; an empty `courses` list means
    the major has no mappable course data (≈110 of 749, mostly minors).
    """
    prog = get_program(program_name)
    if not prog:
        return None

    base = {
        "program_name": prog["program_name"],
        "college": (prog.get("college", "") or "").replace("-", " "),
    }

    # ── 1. Plan-driven (semester tiers) ──────────────────────────────────────
    plan = prog.get("suggested_plan") or {}
    variant = next((v for v in plan.values() if isinstance(v, dict) and v), None)
    if variant:
        sems = sorted(variant.items(), key=lambda kv: _semester_sort_key(kv[0]))
        node_tiers: dict[str, int] = {}
        kind_of: dict[str, str] = {}
        tier_labels: dict[str, str] = {}
        for i, (key, courses) in enumerate(sems, start=1):
            tier_labels[str(i)] = _semester_label(key)
            for c in courses or []:
                for code in _extract_catalog_codes(c.get("description", "")):
                    if code not in node_tiers:
                        node_tiers[code] = i
                        kind_of[code] = "plan"
        if node_tiers:
            return {
                **base,
                "source": "suggested_plan",
                "tier_labels": tier_labels,
                "max_tier": max(node_tiers.values()),
                "courses": _build_map_nodes(node_tiers, kind_of),
            }

    # ── 2. Requirements fallback (prerequisite-depth tiers) ──────────────────
    reqs = prog.get("requirements", {})
    node_codes: list[str] = []
    kind_of = {}
    seen: set[str] = set()

    def _add(raw_code: str, kind: str) -> bool:
        c = _canonical_code(raw_code)
        if c and c in _courses_by_code and c not in seen:
            seen.add(c)
            node_codes.append(c)
            kind_of[c] = kind
            return True
        return False

    for item in reqs.get("prescribed", []):
        if item.get("code"):
            _add(item["code"], "required")
    for item in reqs.get("additional", []):
        for opt in item.get("options", []) or []:
            if opt.get("code"):
                _add(opt["code"], "choice")

    # Transitive feeders so chains like CMPSC 121 → 122 → 221 are visible.
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

    if not node_codes:
        return {**base, "source": "none", "tier_labels": {}, "max_tier": 0, "courses": []}

    node_set = set(node_codes)
    prereq_codes = {
        code: [
            pc for pr in (_courses_by_code.get(code) or {}).get("prerequisites", [])
            for pc in [_canonical_code(pr.get("code", ""))]
            if pc in node_set and pc != code
        ]
        for code in node_codes
    }
    # dedup preserving order
    prereq_codes = {k: list(dict.fromkeys(v)) for k, v in prereq_codes.items()}

    tier: dict[str, int] = {}

    def _depth(code: str, stack: frozenset) -> int:
        if code in tier:
            return tier[code]
        if code in stack:
            return 0
        prs = prereq_codes.get(code, [])
        d = 0 if not prs else 1 + max(_depth(p, stack | {code}) for p in prs)
        tier[code] = d
        return d

    node_tiers = {code: _depth(code, frozenset()) + 1 for code in node_codes}
    max_tier = max(node_tiers.values(), default=0)
    return {
        **base,
        "source": "requirements",
        "tier_labels": {str(t): f"Level {t}" for t in range(1, max_tier + 1)},
        "max_tier": max_tier,
        "courses": _build_map_nodes(node_tiers, kind_of),
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


# ── Prerequisite graph, for the map block ─────────────────────────────────────

_unlock_index: dict[str, list[str]] | None = None


def _build_unlock_index() -> dict[str, list[str]]:
    """code → courses that list it as a prerequisite. Built once, 9k courses."""
    global _unlock_index
    if _unlock_index is None:
        idx: dict[str, list[str]] = {}
        for code, course in _courses_by_code.items():
            for p in course.get("prerequisites", []):
                key = _normalize_code(p.get("code", ""))
                if key:
                    idx.setdefault(key, []).append(code)
        _unlock_index = idx
    return _unlock_index


def parse_prereq_groups(condition: str, codes: list[str]) -> list[list[str]]:
    """Turn a catalog condition into AND-ed groups of OR-ed alternatives.

    "( CMPSC 122 or CMPSC 132 ) and ( CMPSC 360 or MATH 311W )"
        → [[CMPSC 122, CMPSC 132], [CMPSC 360, MATH 311W]]

    That shape is the whole reason the map beats a sentence: prose has to say
    "you need 122 or 132, and also 360 or 311W", which nobody parses.
    """
    text = re.sub(r"^.*?:", "", condition or "", count=1).strip().rstrip(".")
    known = {_normalize_code(c) for c in codes}

    def codes_in(fragment: str) -> list[str]:
        found = [_normalize_code(m) for m in _CODE_RE.findall(fragment.upper())]
        return [c for c in dict.fromkeys(found) if c in known]

    groups: list[list[str]] = []
    if "(" in text:
        for chunk in re.findall(r"\(([^)]*)\)", text):
            got = codes_in(chunk)
            if got:
                groups.append(got)
        # Terms sitting outside the brackets are AND-ed groups of their own.
        outside = codes_in(re.sub(r"\([^)]*\)", " ", text))
        groups += [[c] for c in outside if not any(c in g for g in groups)]
    elif text:
        for chunk in re.split(r"\s+and\s+", text, flags=re.I):
            got = codes_in(chunk)
            if got:
                groups.append(got)

    if not groups and known:
        # No usable condition text: fall back to the and/or mode we can infer.
        ordered = [c for c in (_normalize_code(x) for x in codes) if c]
        course = _courses_by_code.get(_normalize_code(codes[0])) if codes else None
        if _prereq_mode(course, known) == "any":
            groups = [ordered]
        else:
            groups = [[c] for c in ordered]
    return groups


def build_prereq_graph(code: str, completed=None, max_unlocks: int = 6) -> dict | None:
    """Everything the map block needs for one course. None if unknown."""
    target = get_course(code)
    if not target:
        return None

    done = {_canonical_code(c) for c in (completed or [])}
    prereqs = [p for p in get_prerequisites(code) if p.get("code")]
    codes = [p["code"] for p in prereqs]
    condition = next((p.get("condition") for p in prereqs if p.get("condition")), "")

    def node(c):
        info = _courses_by_code.get(_normalize_code(c)) or {}
        return {"code": _normalize_code(c),
                "title": (info.get("title") or "").strip(),
                "done": _canonical_code(c) in done}

    groups = [[node(c) for c in group] for group in parse_prereq_groups(condition, codes)]
    unlocks = [
        {"code": c, "title": (_courses_by_code.get(c, {}).get("title") or "").strip()}
        for c in sorted(_build_unlock_index().get(_normalize_code(code), []))
    ]

    return {
        "target": {"code": _normalize_code(code),
                   "title": (target.get("title") or "").strip(),
                   "credits": target.get("credits")},
        "groups": groups,
        # A group is satisfied when ANY of its options is done; the course is
        # eligible when every group is satisfied.
        "eligible": all(any(n["done"] for n in g) for g in groups) if groups else True,
        "has_record": bool(done),
        "unlocks": unlocks[:max_unlocks],
        "unlocks_more": max(0, len(unlocks) - max_unlocks),
    }
