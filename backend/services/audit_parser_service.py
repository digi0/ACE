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


def parse_whatif_blocks(text: str) -> dict:
    lines = [normalize_line(line) for line in text.splitlines() if normalize_line(line)]

    result = {
        "unsatisfied_blocks": [],
        "remaining_required_courses": [],
        "in_progress_courses": [],
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

    # collect in-progress courses anywhere in the document
    for i, line in enumerate(lines):
        if " IP" in f" {line.upper()} ":
            codes = extract_course_codes(line)
            if codes:
                for code in codes:
                    if code not in result["in_progress_courses"]:
                        result["in_progress_courses"].append(code)

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
    return result


def build_audit_summary(parsed: dict) -> str:
    parts = []

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