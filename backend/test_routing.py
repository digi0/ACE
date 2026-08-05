"""Self-check for intent detection, major classification + record selection.

Run: python -m backend.test_routing
"""
from backend.services.chat_service import (
    classify_major,
    detect_question_intent,
    filter_records_by_scope,
    select_top_records,
)


# (question, expected_intent). Intent decides which grounding a student gets, so
# a misroute is a wrong answer with a confident tone. Every case below was an
# observed misroute before it was a test.
INTENT_CASES = [
    # Two-letter gen-ed codes used to match inside ordinary words, so anything
    # containing "sign"/"things"/"through"/"high" got the Gen Ed table.
    ("what classes should I sign up for next term?", "recommendation"),
    ("what things do I need to graduate?", "student_progress"),
    ("how do things work here?", "general"),
    ("how do I get through my first semester?", "general"),
    # Real gen-ed questions must still route there.
    ("which gen ed courses also count toward my major?", "gen_ed"),
    ("I need a GH course, what do you have?", "gen_ed"),
    ("what satisfies the GQ requirement?", "gen_ed"),

    # Logistics — how the machine works. These all used to land on deadline or
    # general and come back with dates, or with nothing.
    ("how do I register for classes?", "logistics"),
    ("how do I enroll in courses for fall?", "logistics"),
    ("I just enrolled, what do I do first?", "logistics"),
    ("what is a registration hold and how do I clear it?", "logistics"),
    ("how do I use LionPATH?", "logistics"),
    ("when is orientation?", "logistics"),
    ("the class is full, what do I do?", "logistics"),
    # ...without stealing the genuine date questions from deadline.
    ("when is the last day to drop?", "deadline"),
    ("when can I register for spring?", "deadline"),
    ("when does the semester end?", "deadline"),

    # Recommendation — asking ACE to propose, not recite.
    ("what should I take next semester?", "recommendation"),
    ("can you suggest a schedule for me?", "recommendation"),
    ("what courses should I take in the fall?", "recommendation"),
    ("how many credits should I take?", "recommendation"),
    # A plain requirement question is not a proposal.
    ("what math courses are required for my major?", "courses"),

    # Career / clubs / research — ring 3. These sat in the wellbeing list, so a
    # student asking about internships was answered from the CAPS + 988 block.
    ("how do I find an internship?", "career"),
    ("what clubs should I join as a CS major?", "career"),
    ("how do I get involved in undergraduate research?", "career"),
    ("is my resume any good for a software job?", "career"),
    # Distress still wins over the career topic when both are present.
    ("I'm stressed and burnt out about job hunting", "wellbeing"),
    ("I'm overwhelmed", "wellbeing"),

    # Short wellbeing tokens matched inside ordinary words: "org" in "organic",
    # "rec" in "record", "broke" in "broken". A chemistry question was being
    # answered out of the crisis-resources block.
    ("do I need organic chemistry?", "courses"),
    ("can I see my academic record?", "general"),
    ("what are the health requirements?", "gen_ed"),

    # Regressions on intents that already worked.
    ("who do I talk to about my degree requirements?", "contact"),
    ("can STAT 440 substitute for MATH 232?", "substitution"),
    ("do my AP credits count?", "transfer"),
    ("what are the entrance to major requirements?", "etm"),
    ("I'm stressed and overwhelmed", "wellbeing"),
    ("how do I apply for FAFSA?", "financial_aid"),
    ("does OPT affect my enrollment?", "international"),
]


def test_detect_question_intent():
    failures = []
    for question, expected in INTENT_CASES:
        actual = detect_question_intent(question)
        if actual != expected:
            failures.append(f"  {question!r}\n    expected {expected!r}, got {actual!r}")
    assert not failures, "intent misroutes:\n" + "\n".join(failures)


def test_recommendation_context():
    from backend.services.program_service import (
        build_recommendation_context,
        _unmet_prereqs,
    )

    cs = "Computer Science, B.S. (Engineering)"

    # Alternatives are alternatives: CMPSC 121 lists MATH 110 *or* MATH 140, so
    # MATH 140 alone unlocks it. Treating the list as a conjunction told students
    # they were blocked by a course they never needed.
    assert _unmet_prereqs("CMPSC 121", {"MATH 140"}) == [], "an 'or' prereq must unlock"
    assert _unmet_prereqs("CMPSC 121", set()), "with nothing taken it must stay blocked"
    assert _unmet_prereqs("CMPSC 122", {"CMPSC 121"}) == []

    fresh = build_recommendation_context(cs, [])
    assert fresh and fresh["propose"], "a new student must still get a proposal"
    assert fresh["personalised"] is False, "no audit means not personalised"
    assert all(c.get("code") for c in fresh["propose"]), "every proposal names a course"

    # Completed work drops out of the proposal.
    done = [c["code"] for c in fresh["propose"][:2]]
    after = build_recommendation_context(cs, done)
    assert not (set(done) & {c["code"] for c in after["propose"]}), \
        "completed courses must not be proposed again"
    assert after["personalised"] is True

    # A program with no suggested plan returns None so the caller says so
    # instead of inventing a schedule.
    assert build_recommendation_context("Not A Real Program 9999", []) is None


def test_visual_counts_resolve_anaphora_from_history():
    # "map out the prereqs for these classes" names no course — the courses were
    # named a turn ago. Without the history fallback the student asked to see a
    # map and got told there was nothing to draw.
    from backend.services.chat_service import _count_visual_material

    q = "can you map out the pre req map for these classes"
    cs = "Computer Science, B.S. (Engineering)"
    assert _count_visual_material(q, "courses", cs, {}) == {}, "no history → nothing"

    history = [{"role": "assistant",
                "content": "You could take CMPSC 465, CMPSC 431W and STAT 318 next term."}]
    counts = _count_visual_material(q, "courses", cs, {}, history=history)
    assert counts.get("map"), f"history should surface a course to map, got {counts}"


def test_classify_major():
    # The CMPSC handbook documents the UP Engineering program — it must route to RAG.
    assert classify_major("Computer Science, B.S. (Engineering)") == "cs"
    assert classify_major("Computer Science, B.S. (Abington)") == "cs"
    assert classify_major("Data Sciences, B.S. (Science)") == "ds"
    assert classify_major("Psychology, B.A. (Liberal Arts)") == "other"
    assert classify_major(None) is None


def test_select_top_records():
    records = (
        [{"source_type": "pdf_handbook", "id": i} for i in range(6)]
        + [{"source_type": "web_bulletin", "id": i} for i in range(6)]
        + [{"source_type": "excel_vault", "id": i} for i in range(6)]  # retired source
    )
    for intent in ["courses", "student_progress", "substitution", "transfer",
                   "etm", "contact", "gen_ed", "deadline", "general"]:
        picked = select_top_records(records, intent)
        assert picked, f"{intent} selected no records"
        assert all(r["source_type"] != "excel_vault" for r in picked), \
            f"{intent} still selects retired excel_vault records"


def test_filter_records_by_scope():
    records = [
        {"source_name": "CMPSC-handbook-2024-2025.pdf"},
        {"source_name": "CMPSC University Bulletin"},
        {"source_name": "DTSCE-handbook-2024-2025.pdf"},
        {"source_name": "DTSCE University Bulletin"},
    ]
    assert all("CMPSC" in r["source_name"] for r in filter_records_by_scope(records, "cs"))
    assert all("DTSCE" in r["source_name"] for r in filter_records_by_scope(records, "ds"))
    # Unscoped majors are untouched, and an empty scoped set falls back rather
    # than answering from nothing.
    assert filter_records_by_scope(records, "other") == records
    assert filter_records_by_scope(records[:1], "ds") == records[:1]


if __name__ == "__main__":
    test_detect_question_intent()
    test_visual_counts_resolve_anaphora_from_history()
    test_recommendation_context()
    test_classify_major()
    test_select_top_records()
    test_filter_records_by_scope()
    print("routing self-check OK")
