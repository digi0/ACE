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

    # "need" and "take" were bare course keywords, so the two commonest verbs in
    # English decided the topic: "I need to see a doctor" was a course question.
    ("I need to see a doctor", "general"),
    ("how long does it take to get a parking permit?", "general"),
    # ...and they must still carry a course question that names no course word.
    ("do I need organic chemistry?", "courses"),
    ("do I need to take MATH 141?", "courses"),

    # A student asks for "key dates"; only the registrar says "deadlines". This
    # fell to `general`, which claims cards, found none, and apologised.
    ("what are the key dates this semester?", "deadline"),
    ("what important dates should I know this term?", "deadline"),

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


def test_prereq_graph_knows_in_progress_from_done():
    from backend.services.program_service import build_prereq_graph

    # The state that decides "can I take this NEXT fall?". ACE told a student no
    # while they were sitting in one of the two courses it was waiting on.
    g = build_prereq_graph("CMPSC 465", ["CMPSC 132"], in_progress=["CMPSC 360"])
    assert g["eligible"] is False, "not eligible today — 360 is unfinished"
    assert g["on_track"] is True, "but every group is satisfied or under way"
    doing = [n for grp in g["groups"] for n in grp if n["in_progress"]]
    assert [n["code"] for n in doing] == ["CMPSC 360"]

    # Nothing in progress and a group untouched — genuinely blocked.
    blocked = build_prereq_graph("CMPSC 465", ["CMPSC 132"])
    assert blocked["on_track"] is False


def test_transfer_credit_counts_as_satisfied():
    from backend.services.audit_parser_service import satisfied_course_codes

    # Transfer credit appears as "CMPSC XFR100" in the course rows; the only
    # place the real course is named is the requirement header above it.
    audit = ("CMPSC 122 or CMPSC 132-C or higher required\n"
             "Satisfied\n· Units: 3.00 required, 3.00 used\n"
             "FA 2023 CMPSC XFR100 Transfer Credit 3.00 TR\n")
    assert "CMPSC 122" in satisfied_course_codes(audit)

    unmet = audit.replace("Satisfied", "Not Satisfied")
    assert "CMPSC 122" not in satisfied_course_codes(unmet), \
        "'Not Satisfied' must not read as satisfied"


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


def test_distress_rides_along_with_whatever_bracket_wins():
    """Support was withheld from two students in obvious difficulty because
    another bracket claimed the question first. "im failing everything and i
    dont know if i should withdraw" routed to `deadline` and got a withdrawal
    date; "im so behind and stressed i cant even look at lionpath" routed to
    `logistics` and got productivity advice. Neither was offered CAPS.

    `wellbeing` sits 7th in the router's return order. Reordering would be wrong
    — a real logistics question should stay logistics. Withholding care from a
    frightened student because their sentence also mentioned LionPATH is worse,
    so the support resources are additive."""
    from backend.services.chat_service import shows_distress

    for q in ["im failing everything and i dont know if i should withdraw or push through",
              "im so behind and stressed i cant even look at lionpath",
              "i stopped going to class and i dont know what to do anymore",
              "i havent been to class in three weeks"]:
        assert shows_distress(q), f"{q!r} is a student in trouble"

    # ...and an ordinary question does not drag the crisis block in.
    for q in ["when is the late drop deadline", "how do i register for classes",
              "where can i eat on campus", "what math courses do i need"]:
        assert not shows_distress(q), f"{q!r} is not distress"


def test_no_placeholder_rule_appears_when_there_is_no_document():
    """A student who had just said their family could not afford college was told
    to contact "[Advisor Name]". With no uploaded document the instruction to use
    the adviser's name had no referent, and the model manufactured a slot."""
    import inspect, re
    from backend.services import chat_service as cs
    src = inspect.getsource(cs.ask_advisor_stream)
    assert "advisor_rule" in src, "the advisor instruction must be conditional"
    # Collapse the source's own line breaks first — the rule is written across
    # two string literals, so a contiguous substring match on the raw source
    # fails for a reason that has nothing to do with the behaviour.
    flat = re.sub(r'"\s*\n\s*"', "", src)
    assert "NEVER write a placeholder" in flat
    assert "[Advisor Name]" in flat, "the failure mode should be named"
    # And the branch must actually be conditional on having a document.
    assert "if student_doc else" in flat


if __name__ == "__main__":
    test_detect_question_intent()
    test_visual_counts_resolve_anaphora_from_history()
    test_prereq_graph_knows_in_progress_from_done()
    test_transfer_credit_counts_as_satisfied()
    test_recommendation_context()
    test_classify_major()
    test_select_top_records()
    test_filter_records_by_scope()
    test_distress_rides_along_with_whatever_bracket_wins()
    test_no_placeholder_rule_appears_when_there_is_no_document()
    print("routing self-check OK")
