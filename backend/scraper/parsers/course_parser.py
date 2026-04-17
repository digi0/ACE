"""
Parser for course description pages on bulletins.psu.edu.

Key HTML landmarks (confirmed from live pages):
  <div class="courseblock">         — one per course
    <div class="courseblocktitle">
      <div class="course_codetitle">CMPSC 101: Introduction to Programming</div>
      <div class="course_credits">3 Credits</div>
    <div class="courseblockmeta" id="cb-CMPSC101">
      <div class="courseblockdesc">  — description paragraph(s)
      <div class="noindent courseblockextra">  — prereqs, gen-ed, BA/BS notes

courseblockextra contains <p> tags with:
  "Enforced Prerequisite: ..."
  "Bachelor of Arts: ..."
  "General Education: GQ (Quantification)"
  "GenEd Learning Objective: Creative Thinking"
  "A student may receive credit for only one of the following courses:"  (in desc)

Department pages live at:
  /university-course-descriptions/undergraduate/{dept-code}/
The dept sidebar is a <nav id="cl-menu"> with <a href="..."> entries.
"""

import re
import logging
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# Maps the display text to a clean code
GEN_ED_CATEGORIES = {
    "first-year writing": "FYW",
    "fyw": "FYW",
    "quantification": "GQ",
    "natural sciences": "GN",
    "arts": "GA",
    "humanities": "GH",
    "social and behavioral sciences": "GS",
    "human and cultural diversity": "GHD",
    "health and physical activity": "GHP",
    "writing and speaking": "GWS",
    "united states cultures": "US",
    "international cultures": "IL",
    "gq": "GQ",
    "gn": "GN",
    "ga": "GA",
    "gh": "GH",
    "gs": "GS",
    "ghs": "GHS",
    "gha": "GHA",
}


def _text(tag) -> str:
    return tag.get_text(" ", strip=True).replace("\xa0", " ") if tag else ""


def _parse_credits(raw: str) -> str:
    """Normalize credit string: '3 Credits' -> '3', '1-9 Credits/Maximum of 9' -> '1-9'."""
    raw = raw.strip()
    # Extract leading digits / range
    m = re.match(r"([\d][\d\-]*)", raw)
    return m.group(1) if m else raw


def _extract_course_codes(tag: Tag) -> list[str]:
    """Pull all course codes from bubblelink anchors inside a tag."""
    codes = []
    for a in tag.find_all("a", class_="bubblelink"):
        title = a.get("title", "").strip().replace("\xa0", " ")
        if title:
            codes.append(title)
        else:
            codes.append(a.get_text(strip=True).replace("\xa0", " "))
    return [c for c in codes if c]


def _parse_prerequisites(extra_div: Tag) -> list[dict]:
    """
    Parse "Enforced Prerequisite: MATH 21 or satisfactory performance..."
    Returns list of {"code": ..., "condition": ...}
    """
    prereqs: list[dict] = []
    for p in extra_div.find_all("p"):
        text = p.get_text(" ", strip=True)
        if not re.match(r"enforced\s+prerequisite", text, re.I):
            continue
        # Remove the label
        body = re.sub(r"^enforced\s+prerequisite\s*[:\s]+", "", text, flags=re.I).strip()
        # Extract all course codes
        codes = _extract_course_codes(p)
        # Try to parse conditions
        if codes:
            # Condition is everything after the last code
            condition = re.sub(r"^[A-Z]{2,6}\s*\d+[A-Z]?\s*", "", body).strip()
            # Remove leading "or" / "and"
            condition = re.sub(r"^(or|and)\s+", "", condition, flags=re.I).strip()
            for code in codes:
                prereqs.append({"code": code, "enforced": True, "condition": condition})
        else:
            prereqs.append({"code": None, "enforced": True, "condition": body})
    return prereqs


def _parse_gen_ed(extra_div: Tag) -> dict:
    """
    Parse gen-ed designations from courseblockextra paragraphs.
    Handles:
      "Bachelor of Arts: Quantification"
      "General Education: Quantification (GQ)"
      "GenEd Learning Objective: Creative Thinking"
    """
    categories: list[str] = []
    objectives: list[str] = []
    ba_designation: str | None = None
    bs_designation: str | None = None

    for p in extra_div.find_all("p"):
        text = _text(p)
        if not text:
            continue

        if re.match(r"bachelor of arts", text, re.I):
            ba_designation = re.sub(r"bachelor of arts\s*[:\s]+", "", text, flags=re.I).strip()

        elif re.match(r"bachelor of science", text, re.I):
            bs_designation = re.sub(r"bachelor of science\s*[:\s]+", "", text, flags=re.I).strip()

        elif re.match(r"general education\s*[:\s]", text, re.I):
            # e.g. "General Education: Quantification (GQ)"
            body = re.sub(r"general education\s*[:\s]+", "", text, flags=re.I).strip()
            # Try to extract the parenthesised code first
            m = re.search(r"\(([A-Z]{2,4})\)", body)
            if m:
                categories.append(m.group(1))
            else:
                # Map by name
                lower = body.lower()
                for name, code in GEN_ED_CATEGORIES.items():
                    if name in lower:
                        categories.append(code)
                        break

        elif re.match(r"gened\s+learning\s+objective", text, re.I):
            obj = re.sub(r"gened\s+learning\s+objective\s*[:\s]+", "", text, flags=re.I).strip()
            if obj:
                objectives.append(obj)

    result: dict = {}
    if categories:
        result["categories"] = list(dict.fromkeys(categories))  # dedupe, preserve order
    if objectives:
        result["objectives"] = objectives
    if ba_designation:
        result["ba_designation"] = ba_designation
    if bs_designation:
        result["bs_designation"] = bs_designation
    return result


def _parse_cross_listed(desc_div: Tag) -> list[str]:
    """
    Look for "A student may receive credit for only one of the following courses:"
    in the description and extract the course codes.
    """
    text = _text(desc_div)
    if "may receive credit for only one" not in text.lower():
        return []
    # Find the sentence and extract all bubblelinks after it
    codes = _extract_course_codes(desc_div)
    return codes


def parse_course_block(courseblock: Tag, department: str) -> dict | None:
    """Parse a single <div class="courseblock"> into a structured dict."""
    # Title / code
    title_div = courseblock.find("div", class_="course_codetitle")
    if not title_div:
        return None
    raw_title = title_div.get_text(strip=True)
    # Format: "CMPSC 101: Introduction to Programming"
    parts = raw_title.split(":", 1)
    code = parts[0].strip()
    title = parts[1].strip() if len(parts) > 1 else ""

    # Credits (from the non-bubble version)
    credits_div = courseblock.find("div", class_="course_credits")
    credits = _parse_credits(_text(credits_div)) if credits_div else ""

    # Meta section (description + extras)
    meta = courseblock.find("div", class_="courseblockmeta")
    description = ""
    prerequisites: list[dict] = []
    cross_listed: list[str] = []
    gen_ed: dict = {}

    if meta:
        desc_div = meta.find("div", class_="courseblockdesc")
        if desc_div:
            description = _text(desc_div)
            cross_listed = _parse_cross_listed(desc_div)

        for extra in meta.find_all("div", class_="courseblockextra"):
            # Check what kind of extra this is
            full_text = _text(extra)
            if re.match(r"enforced\s+prereq", full_text, re.I):
                prerequisites.extend(_parse_prerequisites(extra))
            elif re.search(r"general education|bachelor of|gened\s+learning", full_text, re.I):
                gen_ed.update(_parse_gen_ed(extra))

    result: dict = {
        "code": code,
        "title": title,
        "credits": credits,
        "department": department.upper(),
        "description": description,
    }
    if prerequisites:
        result["prerequisites"] = prerequisites
    if cross_listed:
        result["cross_listed"] = cross_listed
    if gen_ed:
        result["gen_ed"] = gen_ed

    return result


def parse_department_page(soup: BeautifulSoup, dept_code: str) -> list[dict]:
    """Parse all courses on a department page."""
    courses: list[dict] = []
    container = soup.find("div", class_="sc_sccoursedescs")
    if not container:
        logger.warning("No sc_sccoursedescs found for dept %s", dept_code)
        return courses

    for block in container.find_all("div", class_="courseblock", recursive=False):
        course = parse_course_block(block, dept_code)
        if course:
            courses.append(course)

    logger.info("  Parsed %d courses for %s", len(courses), dept_code)
    return courses


def parse_department_index(soup: BeautifulSoup) -> list[dict]:
    """
    Parse the /university-course-descriptions/undergraduate/ index page.
    Returns [{"code": "CMPSC", "name": "Computer Science", "url": "..."}]
    """
    depts: list[dict] = []
    nav = soup.find("nav", id="cl-menu")
    if not nav:
        # Fall back: look in the main content az_sitemap
        nav = soup.find("div", class_="az_sitemap")
    if not nav:
        return depts

    for a in nav.find_all("a", href=True):
        href = a["href"]
        if "/university-course-descriptions/undergraduate/" not in href:
            continue
        slug = href.rstrip("/").split("/")[-1]
        if not slug:
            continue
        text = a.get_text(strip=True)
        # "Computer Science (CMPSC)" → name="Computer Science", code="CMPSC"
        m = re.match(r"^(.*?)\s*\(([A-Z0-9\-]+)\)\s*$", text)
        if m:
            name = m.group(1).strip()
            code = m.group(2).strip()
        else:
            name = text
            code = slug.upper()
        depts.append({
            "code": code,
            "name": name,
            "slug": slug,
            "url": f"https://bulletins.psu.edu{href}",
        })

    return depts
