"""
Parser for individual program pages on bulletins.psu.edu.

Key HTML landmarks (confirmed from live pages):
  <h1 class="page-title">       — program name
  <p id="program-code">         — "Plan Code: X and Y"
  <div id="campus-list">        — begin/end campus
  <div id="programrequirementstextcontainer">  — all requirements
    <table class="sc_sctable"> — credits summary table
    <table class="sc_courselist"> — course rows
  <div id="suggestedacademicplantextcontainer"> — semester plan

Course row classes in sc_courselist:
  .areaheader   — section header (Prescribed Courses / Additional Courses)
  .areasubheader — grade requirement note
  .orclass      — "or" alternative for the previous non-or row
  blockindent   — pool member (indented, inside a .codecol)
  courselistcomment — free-text comment (pool header, footnotes, etc.)
"""

import re
import logging
from typing import Any

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _text(tag) -> str:
    return tag.get_text(" ", strip=True).replace("\xa0", " ") if tag else ""


def _extract_code_from_td(td: Tag) -> str:
    """Extract course code from a codecol <td>. Handles normal and orclass variants."""
    if td is None:
        return ""
    a = td.find("a", class_="bubblelink")
    if a:
        code = a.get("title", a.get_text(strip=True)).strip()
    else:
        code = td.get_text(strip=True)
        # Strip leading "or "
        code = re.sub(r"^or\s+", "", code, flags=re.I).strip()
    # Normalize non-breaking spaces to regular spaces
    return code.replace("\xa0", " ")


def _parse_credits(text: str):
    """
    Return credits as int if whole number, or string if range / variable.
    e.g. "3" -> 3,  "106-108" -> "106-108",  "1-9" -> "1-9"
    """
    text = text.strip()
    if not text:
        return None
    if re.match(r"^\d+$", text):
        return int(text)
    return text  # range or variable


def _parse_gen_ed_overlap(paragraph: str) -> dict:
    """
    Parse e.g. "9 credits of GN courses; 6 credits of GQ courses; 9 credits of GWS courses"
    -> {"GN": 9, "GQ": 6, "GWS": 9}
    Also handles "9 GN credits" and similar variations.
    """
    overlap: dict[str, int] = {}
    # Pattern: "N credits of XX" or "N XX credits"
    for m in re.finditer(r"(\d+)\s+credits?\s+of\s+([A-Z]{2,4})", paragraph, re.I):
        overlap[m.group(2).upper()] = int(m.group(1))
    for m in re.finditer(r"(\d+)\s+([A-Z]{2,4})\s+credits?", paragraph, re.I):
        code = m.group(2).upper()
        if code not in overlap:
            overlap[code] = int(m.group(1))
    return overlap


# ── Campus parsing ────────────────────────────────────────────────────────────

def _parse_campuses(soup: BeautifulSoup) -> dict:
    campus_div = soup.find("div", id="campus-list")
    if not campus_div:
        return {"begin": [], "end": []}

    cols = campus_div.find_all("div", class_="col-sm-6")
    result = {}
    for col in cols:
        header = col.find("strong")
        if not header:
            continue
        label = header.get_text(strip=True).lower()
        # All text after the header
        text = col.get_text(" ", strip=True)
        text = re.sub(re.escape(header.get_text(strip=True)), "", text, count=1).strip()
        campuses = [c.strip() for c in re.split(r",\s*|\band\b", text) if c.strip()]
        if "begin" in label:
            result["begin"] = campuses
        elif "end" in label:
            result["end"] = campuses

    # Combine: unique campuses mentioned in both begin and end
    all_campuses = list(dict.fromkeys(result.get("begin", []) + result.get("end", [])))
    return {"begin": result.get("begin", []), "end": result.get("end", []), "all": all_campuses}


# ── Credits summary table ─────────────────────────────────────────────────────

def _parse_degree_summary(req_container: Tag) -> dict:
    """Parse the sc_sctable that lists Gen Ed / Major credits and the overlap note."""
    summary: dict[str, Any] = {}

    # Total credits from the bold lead sentence
    bold_text = ""
    for strong in req_container.find_all("strong"):
        t = strong.get_text(" ", strip=True)
        if "minimum of" in t.lower() or "credits is required" in t.lower():
            bold_text = t
            break
    m = re.search(r"minimum of (\d+) credits?", bold_text, re.I)
    if m:
        summary["total_credits"] = int(m.group(1))

    # sc_sctable rows
    sctable = req_container.find("table", class_="sc_sctable")
    if sctable:
        for tr in sctable.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) >= 2:
                label = tds[0].get_text(strip=True).lower()
                val = tds[1].get_text(strip=True)
                if "general education" in label:
                    summary["gen_ed_credits"] = _parse_credits(val)
                elif "requirements for the major" in label or "major" in label:
                    summary["major_credits"] = val  # keep as string (may be range)

    # Gen Ed overlap note (the bold paragraph after the table)
    if sctable:
        next_sibling = sctable.find_next_sibling()
        while next_sibling:
            text = _text(next_sibling)
            if re.search(r"credits.*included.*major|GN|GQ|GWS|GA|GH|GS", text, re.I):
                summary["gen_ed_overlap"] = _parse_gen_ed_overlap(text)
                summary["gen_ed_overlap_note"] = text
                break
            next_sibling = next_sibling.find_next_sibling()

    return summary


# ── Course list table parser ──────────────────────────────────────────────────

def _is_pool_member(td_code: Tag) -> bool:
    return bool(td_code and td_code.find("div", class_="blockindent"))


def _parse_course_list(table: Tag) -> dict:
    """
    Walk sc_courselist rows and produce:
      {"prescribed": [...], "additional": [...]}

    Prescribed items: {"code", "title", "credits", "min_grade"}
    Additional items (choice): {"type":"choice", "description", "credits", "options":[{"code","title"}]}
    Additional items (pool):   {"type":"pool", "description", "credits", "options":[{"code","title"}]}
    Additional items (comment):{"type":"comment", "description"}
    """
    prescribed: list[dict] = []
    additional: list[dict] = []
    current_section = None   # "prescribed" | "additional"
    current_min_grade = None

    # State for building the current item
    current_choice: dict | None = None  # choice group leader
    in_pool = False
    pool: dict | None = None            # current pool being built

    def _flush_choice():
        nonlocal current_choice
        if current_choice is None:
            return
        if current_section == "prescribed":
            prescribed.append(current_choice)
        elif current_section == "additional":
            opts = current_choice.get("options", [])
            if len(opts) <= 1:
                # Single course with no alternatives — simple prescribed-style item
                additional.append({
                    "type": "choice",
                    "description": current_choice.get("title", ""),
                    "credits": current_choice.get("credits"),
                    "options": [{"code": current_choice["code"], "title": current_choice.get("title", "")}],
                })
            else:
                additional.append({
                    "type": "choice",
                    "description": current_choice.get("title", ""),
                    "credits": current_choice.get("credits"),
                    "options": opts,
                })
        current_choice = None

    def _flush_pool():
        nonlocal pool, in_pool
        if pool and pool.get("options"):
            if current_section == "additional":
                additional.append(pool)
            pool = None
        in_pool = False

    rows = table.find_all("tr")
    for tr in rows:
        classes = tr.get("class", [])
        cls_str = " ".join(classes)

        # ── Section / subsection headers ──────────────────────────────────
        if "areaheader" in cls_str and "areasubheader" not in cls_str:
            header_text = _text(tr).lower()
            _flush_choice()
            _flush_pool()
            if "prescribed" in header_text:
                current_section = "prescribed"
            elif "additional" in header_text:
                current_section = "additional"
            elif "general education" in header_text:
                current_section = "gened"
            elif "university degree" in header_text:
                current_section = "university"
            else:
                current_section = "other"
            current_min_grade = None
            continue

        if "areasubheader" in cls_str:
            sub_text = _text(tr)
            if re.search(r"grade of ([A-D][+-]?)", sub_text, re.I):
                m = re.search(r"grade of ([A-D][+-]?)", sub_text, re.I)
                current_min_grade = m.group(1) if m else None
            continue

        if current_section not in ("prescribed", "additional"):
            continue

        tds = tr.find_all(["td", "th"])
        if not tds:
            continue

        # ── OR-class row (alternative course) ─────────────────────────────
        if "orclass" in cls_str:
            td_code = tr.find("td", class_="codecol")
            code = _extract_code_from_td(td_code)
            # Title is in the next td or the codecol itself after "or"
            tds_all = tr.find_all("td")
            title = ""
            for td in tds_all:
                if "codecol" not in (td.get("class") or []):
                    title = td.get_text(strip=True)
                    break
            if current_choice is not None:
                opts = current_choice.setdefault("options", [])
                if not opts:
                    # First time seeing alternatives — add the leader
                    opts.append({"code": current_choice["code"], "title": current_choice.get("title", "")})
                opts.append({"code": code, "title": title})
            continue

        # ── Determine if this is a comment row ─────────────────────────────
        comment_span = tr.find("span", class_="courselistcomment")
        if comment_span and "areaheader" not in (comment_span.get("class") or []):
            comment_text = _text(comment_span)
            credits_td = tr.find("td", class_="hourscol")
            cred_val = _parse_credits(_text(credits_td)) if credits_td else None

            if re.match(r"select\s+\d+", comment_text, re.I) or (
                cred_val and re.search(r"following", comment_text, re.I)
            ):
                # Pool header — flush previous, start new pool
                _flush_choice()
                _flush_pool()
                in_pool = True
                pool = {
                    "type": "pool",
                    "description": comment_text,
                    "credits": cred_val,
                    "options": [],
                }
            else:
                # Standalone comment
                _flush_choice()
                _flush_pool()
                additional.append({"type": "comment", "description": comment_text})
            continue

        # ── Regular course row ─────────────────────────────────────────────
        td_code = tr.find("td", class_="codecol")
        if td_code is None:
            continue

        # Pool member? (blockindent inside codecol)
        if _is_pool_member(td_code):
            code = _extract_code_from_td(td_code)
            tds_all = tr.find_all("td")
            title = ""
            for td in tds_all:
                cls = td.get("class") or []
                if "codecol" not in cls and "hourscol" not in cls:
                    title = td.get_text(strip=True)
                    break
            if in_pool and pool is not None:
                pool["options"].append({"code": code, "title": title})
            continue

        # Not a pool member — flush pool if open
        if in_pool:
            _flush_pool()

        # Flush previous choice group
        _flush_choice()

        # Extract this row's course
        code = _extract_code_from_td(td_code)
        tds_all = tr.find_all("td")
        title = ""
        credits = None
        for td in tds_all:
            cls = td.get("class") or []
            if "codecol" not in cls and "hourscol" not in cls:
                title = td.get_text(strip=True)
            if "hourscol" in cls:
                credits = _parse_credits(td.get_text(strip=True))

        if not code:
            continue

        if current_section == "prescribed":
            current_choice = {
                "code": code,
                "title": title,
                "credits": credits,
                "min_grade": current_min_grade,
            }
        else:
            current_choice = {
                "code": code,
                "title": title,
                "credits": credits,
            }

    # Flush anything remaining
    _flush_choice()
    _flush_pool()

    return {"prescribed": prescribed, "additional": additional}


# ── Suggested academic plan ───────────────────────────────────────────────────

def _parse_suggested_plan(plan_container: Tag) -> dict:
    """
    Parse sc_plangrid tables.
    Returns {plan_label: {semester_label: [{code, credits}]}}
    """
    if not plan_container:
        return {}

    plans: dict[str, dict] = {}

    for h4 in plan_container.find_all(["h3", "h4"]):
        plan_label = h4.get_text(strip=True)
        table = h4.find_next_sibling("table", class_="sc_plangrid")
        if not table:
            continue

        semesters: dict[str, list] = {}
        current_year = ""
        col_headers: list[str] = []  # e.g. ["Fall", "Spring"]

        for tr in table.find_all("tr"):
            classes = " ".join(tr.get("class", []))

            if "plangridyear" in classes:
                current_year = tr.get_text(strip=True)
                col_headers = []
                continue

            if "plangridterm" in classes:
                col_headers = []
                for th in tr.find_all("th"):
                    t = th.get_text(strip=True)
                    if t and "Credits" not in t:
                        col_headers.append(t)
                continue

            if "plangridsum" in classes:
                continue

            # Data row — alternating columns per semester
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue

            # Two semesters per row; pairs are (codecol, hourscol)
            pairs = []
            i = 0
            while i + 1 < len(tds):
                pairs.append((tds[i], tds[i + 1]))
                i += 2

            for idx, (code_td, hour_td) in enumerate(pairs):
                if idx >= len(col_headers):
                    break
                sem_label = f"{current_year} {col_headers[idx]}".strip()
                sem_key = sem_label.lower().replace(" ", "_")
                if sem_key not in semesters:
                    semesters[sem_key] = []

                raw_text = code_td.get_text(" ", strip=True)
                # Remove footnote superscripts like *‡#†
                raw_text = re.sub(r"[\*‡#†]+", "", raw_text).strip()

                credits_text = hour_td.get_text(strip=True)
                try:
                    credits_val = int(credits_text) if credits_text else None
                except ValueError:
                    credits_val = None

                if raw_text and raw_text not in ("", " "):
                    semesters[sem_key].append({
                        "description": raw_text,
                        "credits": credits_val,
                    })

        if semesters:
            plans[plan_label] = semesters

    return plans


# ── Main entry point ──────────────────────────────────────────────────────────

def parse_program_page(soup: BeautifulSoup, url: str, college_slug: str) -> dict | None:
    """
    Parse a program page and return a structured dict.
    Returns None if the page doesn't look like a valid program page.
    """
    # ── Title ─────────────────────────────────────────────────────────────
    h1 = soup.find("h1", class_="page-title")
    if not h1:
        logger.warning("No h1.page-title found at %s", url)
        return None
    program_name = h1.get_text(strip=True)

    # ── Degree type from title suffix ─────────────────────────────────────
    degree_type = "unknown"
    name_lower = program_name.lower()
    if any(x in name_lower for x in [", b.s.", ", b.a.", ", b.f.a.", ", b.b.a.", ", b.m.", ", b.s.ed", ", b.a.e", ", b.eng", ", b.des", ", b.arch"]):
        degree_type = "baccalaureate"
    elif ", a." in name_lower or "a.engt" in name_lower or "a.a.s" in name_lower:
        degree_type = "associate"
    elif "minor" in name_lower:
        degree_type = "minor"
    elif "certificate" in name_lower:
        degree_type = "certificate"

    # ── Plan code ─────────────────────────────────────────────────────────
    plan_code_tag = soup.find("p", id="program-code")
    plan_codes: list[str] = []
    if plan_code_tag:
        raw = plan_code_tag.get_text(strip=True)
        raw = re.sub(r"Plan Code[:\s]+", "", raw, flags=re.I)
        plan_codes = [p.strip() for p in re.split(r"\s+and\s+|,\s*", raw) if p.strip()]

    # ── Campuses ──────────────────────────────────────────────────────────
    campus_info = _parse_campuses(soup)

    # ── Requirements ──────────────────────────────────────────────────────
    req_container = soup.find("div", id="programrequirementstextcontainer")
    degree_summary: dict = {}
    requirements: dict = {"prescribed": [], "additional": []}

    if req_container:
        degree_summary = _parse_degree_summary(req_container)
        course_table = req_container.find("table", class_="sc_courselist")
        if course_table:
            requirements = _parse_course_list(course_table)

    # ── Suggested plan ────────────────────────────────────────────────────
    plan_container = soup.find("div", id="suggestedacademicplantextcontainer")
    suggested_plan = _parse_suggested_plan(plan_container) if plan_container else {}

    return {
        "program_name": program_name,
        "degree_type": degree_type,
        "college": college_slug,
        "plan_codes": plan_codes,
        "campuses": campus_info.get("all", []),
        "campuses_begin": campus_info.get("begin", []),
        "campuses_end": campus_info.get("end", []),
        "total_credits": degree_summary.get("total_credits"),
        "gen_ed_credits": degree_summary.get("gen_ed_credits"),
        "major_credits": degree_summary.get("major_credits"),
        "gen_ed_overlap": degree_summary.get("gen_ed_overlap", {}),
        "gen_ed_overlap_note": degree_summary.get("gen_ed_overlap_note", ""),
        "requirements": requirements,
        "suggested_plan": suggested_plan,
        "url": url,
    }
