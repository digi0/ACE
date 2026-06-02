import re


def normalize_line(line: str) -> str:
    return " ".join(line.split()).strip()


def extract_course_codes(text: str) -> list[str]:
    matches = re.findall(r"\b([A-Z]{2,6}\s?\d{3}[A-Z]?)\b", text.upper())
    seen = []
    for m in matches:
        code = " ".join(m.split())
        if code not in seen:
            seen.append(code)
    return seen


def parse_units_line(line: str) -> dict:
    # Example: Units: 40.00 required, 34.00 used, 6.00 needed
    m = re.search(
        r"([0-9]+(?:\.[0-9]+)?)\s+required,\s+([0-9]+(?:\.[0-9]+)?)\s+used(?:,\s+([0-9]+(?:\.[0-9]+)?)\s+needed)?",
        line,
        flags=re.IGNORECASE,
    )
    if not m:
        return {}

    return {
        "required": float(m.group(1)),
        "used": float(m.group(2)),
        "needed": float(m.group(3)) if m.group(3) else 0.0,
    }


# Course-instance rows in a LionPATH audit / what-if extract as, e.g.:
#   "FA 2022 MATH  140 CALC ANLY "   (term, subject, cat#, partial title)
#   "GEOM I"                          (title continuation)
#   "4.00 C+"                         (units, grade — 1-3 lines below)
_TERM = r"(?:FA|SP|SU|WI|SM)\s+\d{4}"
_COURSE_ROW_RE = re.compile(rf"^{_TERM}\s+([A-Z]{{2,6}})\s+(\d{{3}}[A-Z]?)\b")
_UNITS_GRADE_RE = re.compile(r"\b(\d+\.\d{2})\s+(IP|TR|CR|WD|LD|XF|NG|R|[A-DF][+-]?)\b")
_PASSING_GRADES = {"A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "TR", "CR"}


def parse_cumulative_gpa(lines: list[str]) -> float | None:
    """Pull the cumulative GPA, e.g. the 'Cum GPA: 2.990' line."""
    for line in lines:
        m = re.search(r"Cum GPA:\s*([0-9]+\.[0-9]+)", line)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return None


def parse_course_rows(lines: list[str]) -> tuple[list[dict], list[dict]]:
    """Pair each course-instance row with its units+grade line.

    Returns (completed, in_progress); each entry is {code, grade, units, term}.
    Completed = a passing letter or transfer grade; in_progress = grade 'IP'.
    """
    completed: list[dict] = []
    in_progress: list[dict] = []
    completed_codes: set[str] = set()
    ip_codes: set[str] = set()
    n = len(lines)

    for i, line in enumerate(lines):
        m = _COURSE_ROW_RE.match(line)
        if not m:
            continue
        code = f"{m.group(1)} {m.group(2)}"
        parts = line.split()
        term = f"{parts[0]} {parts[1]}" if len(parts) >= 2 else ""

        # find the units+grade within the next few rows, stopping if we hit the
        # next course row (so we don't steal its grade)
        grade = units = None
        for k in range(i, min(i + 5, n)):
            if k > i and _COURSE_ROW_RE.match(lines[k]):
                break
            gm = _UNITS_GRADE_RE.search(lines[k])
            if gm:
                units = float(gm.group(1))
                grade = gm.group(2)
                break
        if grade is None:
            continue

        entry = {"code": code, "grade": grade, "units": units, "term": term}
        if grade == "IP":
            if code not in ip_codes:
                ip_codes.add(code)
                in_progress.append(entry)
        elif grade in _PASSING_GRADES:
            if code not in completed_codes:
                completed_codes.add(code)
                completed.append(entry)
    return completed, in_progress


def parse_whatif_blocks(text: str) -> dict:
    lines = [normalize_line(line) for line in text.splitlines() if normalize_line(line)]

    result = {
        "unsatisfied_blocks": [],
        "remaining_required_courses": [],
        "in_progress_courses": [],
        "completed_courses": [],
        "cumulative_gpa": None,
        "earned_credits": 0.0,
        "overall_totals": {},
        "advisor": None,
    }

    # extract advisor name (appears as "Advisor:" followed by "LastName,FirstName")
    for idx, line in enumerate(lines):
        if line.upper().startswith("ADVISOR:"):
            # name may be on the same line or the next
            inline = line[len("Advisor:"):].strip()
            if inline:
                result["advisor"] = inline.replace(",", ", ")
            elif idx + 1 < len(lines):
                result["advisor"] = lines[idx + 1].strip().replace(",", ", ")
            break

    i = 0
    while i < len(lines):
        line = lines[i]
        upper = line.upper()

        # overall totals — match section titles that end with "Total" or "Total units"
        # e.g. "Computer Science Major, (CMPSC_BS) Total" or "...Total units"
        if upper.endswith("TOTAL") or upper.endswith("TOTAL UNITS"):
            for k in range(i + 1, min(i + 6, len(lines))):
                k_upper = lines[k].upper()
                if "REQUIRED" in k_upper and "USED" in k_upper:
                    units = parse_units_line(lines[k])
                    if units:
                        result["overall_totals"][line] = units
                    break

        # unsatisfied requirement block
        if "NOT SATISFIED:" in upper:
            block = {
                "title": lines[i - 1] if i > 0 else "Unknown Requirement",
                "status_line": line,
                "units": {},
                "course_list": [],
                "supporting_lines": [],
            }

            # units line usually follows soon after (may be preceded by cross-listing notes)
            for j in range(i + 1, min(i + 20, len(lines))):
                if "REQUIRED" in lines[j].upper() and "USED" in lines[j].upper():
                    block["units"] = parse_units_line(lines[j])
                    break

            # scan the next lines until another major block starts
            j = i + 1
            while j < len(lines):
                current = lines[j]
                current_upper = current.upper()

                # stop when next major section begins
                if j > i + 1 and (
                    "SATISFIED" in current_upper
                    or "NOT SATISFIED:" in current_upper
                    or current_upper.endswith("REQUIRED")
                    or current_upper.endswith("UNITS REQUIRED")
                    or current_upper.startswith("TERM SUBJECT")
                ):
                    # keep going a little for specific course lists in prescribed sections
                    pass

                # explicit course list lines
                if "COMPLETE THE FOLLOWING" in current_upper:
                    codes = extract_course_codes(current)
                    for code in codes:
                        if code not in block["course_list"]:
                            block["course_list"].append(code)

                if current_upper.startswith("COURSE LIST:"):
                    codes = extract_course_codes(current)
                    for code in codes:
                        if code not in block["course_list"]:
                            block["course_list"].append(code)

                # prescribed-course term rows may contain still-needed required courses
                # We only want rows that include WD/LD/F/unsat-ish indicators or are named in the report as missing
                if any(tag in current_upper for tag in [" LD", " WD", " W ", " F ", " UNSAT", "NOT SATISFACTORY"]):
                    codes = extract_course_codes(current)
                    for code in codes:
                        if code not in block["course_list"]:
                            block["course_list"].append(code)

                block["supporting_lines"].append(current)

                # break on next major titled section
                if j > i + 3 and (
                    current_upper.startswith("SUPPORTING COURSES")
                    or current_upper.startswith("COMPUTER SCIENCE MAJOR")
                    or current_upper.startswith("COMMUNICATIONS")
                    or current_upper.startswith("QUANTIFICATION")
                    or current_upper.startswith("GENERAL EDUCATION")
                    or current_upper.startswith("FOREIGN LANGUAGE")
                    or current_upper.startswith("DEPARTMENT LIST")
                    or current_upper.startswith("FIRST-YEAR SEMINAR")
                    or current_upper.startswith("ADDITIONAL COMPUTER SCIENCE COURSES")
                ):
                    break

                j += 1

            result["unsatisfied_blocks"].append(block)
            i = j
            continue

        i += 1

    # special high-value extraction for the prescribed-courses block:
    # if a block title suggests prescribed/core courses, prioritize withdrawn/failed required courses
    remaining_required = []
    for block in result["unsatisfied_blocks"]:
        title_upper = block["title"].upper()
        if "PRESCRIBED" in title_upper or "C OR HIGHER REQUIRED" in title_upper:
            for code in block["course_list"]:
                if code not in remaining_required:
                    remaining_required.append(code)

    result["remaining_required_courses"] = remaining_required

    # paired course-row extraction (fixes the split-line IP bug) + GPA/credits
    completed_courses, in_progress_detailed = parse_course_rows(lines)
    result["completed_courses"] = completed_courses
    result["in_progress_courses"] = [c["code"] for c in in_progress_detailed]
    result["cumulative_gpa"] = parse_cumulative_gpa(lines)
    result["earned_credits"] = round(
        sum(c.get("units") or 0 for c in completed_courses), 2
    )
    return result


def build_audit_summary(parsed: dict) -> str:
    parts = []

    if parsed.get("cumulative_gpa") is not None:
        parts.append(f"Cumulative GPA: {parsed['cumulative_gpa']:.3f}")

    if parsed.get("completed_courses"):
        parts.append(
            f"Completed courses on record: {len(parsed['completed_courses'])} "
            f"(~{parsed.get('earned_credits', 0):.0f} credits)."
        )

    if parsed.get("remaining_required_courses"):
        parts.append("Remaining required/core courses detected:")
        for code in parsed["remaining_required_courses"]:
            parts.append(f"- {code}")

    if parsed.get("unsatisfied_blocks"):
        parts.append("Unsatisfied requirement blocks detected:")
        for block in parsed["unsatisfied_blocks"][:15]:
            title = block.get("title", "Unknown Requirement")
            units = block.get("units", {})
            needed = units.get("needed")
            if needed is not None:
                parts.append(f"- {title} ({needed:.2f} units needed)")
            else:
                parts.append(f"- {title}")

    if parsed.get("in_progress_courses"):
        parts.append("In-progress courses detected:")
        for code in parsed["in_progress_courses"][:15]:
            parts.append(f"- {code}")

    if parsed.get("overall_totals"):
        parts.append("Overall totals detected:")
        for title, units in parsed["overall_totals"].items():
            parts.append(
                f"- {title}: required {units.get('required', 0):.2f}, "
                f"used {units.get('used', 0):.2f}, needed {units.get('needed', 0):.2f}"
            )

    return "\n".join(parts) if parts else "No audit summary extracted."