"""Self-check for reading a what-if report correctly.

Transfer credit is the thing this file exists for. A student with 66 of 120
credits used was reported as having ONE completed course and 0.75 credits
earned, and ACE told them they were ineligible for a course they had cleared —
because the course rows say "CMPSC XFR100" and only the requirement header above
says which course that credit is for.

    python -m backend.test_audit
"""

from backend.services.audit_parser_service import (
    merge_satisfied_requirements, parse_satisfied_requirements,
    satisfied_course_codes,
)

AUDIT = """
MATH 140-C or higher required
Satisfied
· Units: 3.00 required, 3.00 used
FA 2023 MATH XFRGQ1 Transfer Credit 3.00 TR
CMPSC 122 or CMPSC 132-C or higher required
Satisfied
· Units: 3.00 required, 3.00 used
FA 2023 CMPSC XFR100 Transfer Credit 3.00 TR
CMPSC 465-C or higher required
Not Satisfied
· Units: 3.00 required, 0.00 used
"""


def test_satisfied_blocks_are_read():
    rows = parse_satisfied_requirements(AUDIT)
    states = {r["state"] for r in rows}
    assert "satisfied" in states and "unsatisfied" in states
    codes = satisfied_course_codes(AUDIT)
    assert {"MATH 140", "CMPSC 122", "CMPSC 132"} <= codes


def test_not_satisfied_is_not_satisfied():
    # "Not Satisfied" contains "Satisfied" as a substring — the reason this is
    # asserted rather than assumed.
    assert "CMPSC 465" not in satisfied_course_codes(AUDIT)


def test_merge_adds_courses_without_inventing_credits():
    parsed = {"completed_courses": [{"code": "CHEM 113", "units": 0.75}],
              "earned_credits": 0.75,
              "overall_totals": {"Total": {"required": 120.0, "used": 66.49}}}
    merge_satisfied_requirements(parsed, AUDIT)

    codes = {c["code"] for c in parsed["completed_courses"]}
    assert {"CHEM 113", "CMPSC 122", "MATH 140"} <= codes, codes
    assert all(c.get("units", 0) == 0 for c in parsed["completed_courses"]
               if c.get("source") == "satisfied requirement"), \
        "requirement blocks must not add credits — the rows already counted them"

    # The audit's own stated total beats our arithmetic over the rows.
    assert parsed["earned_credits"] == 66.49
    assert parsed["earned_credits_source"] == "audit total"


def test_merge_is_idempotent():
    parsed = {"completed_courses": [], "earned_credits": 0}
    merge_satisfied_requirements(parsed, AUDIT)
    first = len(parsed["completed_courses"])
    merge_satisfied_requirements(parsed, AUDIT)
    assert len(parsed["completed_courses"]) == first, \
        "re-reading a document must not duplicate its courses"


def test_no_audit_text_is_harmless():
    parsed = {"completed_courses": [], "earned_credits": 0}
    merge_satisfied_requirements(parsed, "")
    assert parsed["completed_courses"] == []


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("\nall audit checks passed")
