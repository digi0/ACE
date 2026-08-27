"""Self-check for the procedures dataset and matcher.

Runs against the committed procedures.json — no network, no LLM.

    python -m backend.test_procedures
"""

from backend.services import procedures_service as ps


def test_dataset_is_present_and_shaped():
    procs = ps.load_procedures()
    assert len(procs) >= 15, f"expected the full procedure set, got {len(procs)}"
    for p in procs:
        assert p["title"], "every procedure needs a title"
        assert p["topic"] in ps.TOPIC_TRIGGERS, f"{p['title']} has unknown topic {p['topic']}"
        assert p["source_url"].startswith("https://"), p["source_url"]
        # A procedure with no steps and no explanation cannot help anyone.
        assert p.get("steps") or p.get("what_it_is"), f"{p['title']} is empty"


def test_the_retroactive_path_exists():
    # The question ACE could not answer at all before this dataset.
    titles = [p["title"].lower() for p in ps.load_procedures()]
    assert any("petition" in t for t in titles), "the petition path must be covered"


def test_missing_a_deadline_routes_to_the_petition():
    # The whole point: once the deadline is behind them, the calendar is the
    # wrong answer and the petition is the right one.
    for q in [
        "I missed the late drop deadline, what can I do?",
        "the deadline has passed, can I still drop?",
        "it's too late to withdraw, is there any way?",
    ]:
        assert ps.detect_topics(q)[0] == "petition", f"{q!r} → {ps.detect_topics(q)}"


# How a student describes their situation, per topic. Written deliberately in
# their words rather than the registrar's. When this table was first run, 36 of
# 39 cases matched NOTHING — the procedures dataset was reachable only by someone
# who already knew the institutional vocabulary, which is the opposite of who
# needs it. Add to this table before adding trigger phrases.
STUDENT_PHRASINGS = {
    "withdrawal": [
        "I want to quit school this semester",
        "I'm thinking of dropping out",
        "I stopped going to my classes, what happens",
        "can I leave in the middle of the term",
        "how do I get out of this semester entirely",
        "I don't want to be enrolled anymore",
    ],
    "leave_of_absence": [
        "I need to take a year off",
        "can I pause my degree for a bit",
        "I want to step away for a semester and come back",
        "I'm going through something and need time",
        "family emergency, I can't be here this term",
    ],
    "re_enrollment": [
        "I dropped out two years ago and want to finish",
        "how do I come back after leaving",
        "I want to start again at Penn State",
        "I was gone a while, can I return",
        "I got suspended, how do I get back in",
    ],
    "late_drop": [
        "I want to get out of one class",
        "can I quit just one course",
        "how do I remove a class from my schedule",
        "I want to unenroll from a class",
    ],
    "petition": [
        "is there any way to appeal this",
        "can I ask for an exception",
        "who decides if I can get out of this rule",
        "I have a really good reason, can they make an exception",
    ],
    "registration": [
        "I can't sign up for classes yet",
        "why can't I enroll",
        "when does my registration window open",
        "the system won't let me add anything",
    ],
    "change_program": [
        "I want to switch what I'm studying",
        "I don't like my major anymore",
        "can I move to a different campus",
        "I want to study something else",
    ],
    "graduation": [
        "how do I make sure I actually graduate",
        "what do I do to walk in May",
        "am I signed up to graduate",
        "how do I get my diploma",
    ],
    "transcripts": [
        "I need my grades sent to another school",
        "how do I get a copy of my record",
        "grad school wants my academic history",
    ],
}


def test_every_topic_is_reachable_in_plain_english():
    misses = []
    for topic, questions in STUDENT_PHRASINGS.items():
        for q in questions:
            if topic not in ps.detect_topics(q):
                misses.append(f"  {topic}: {q!r} → {ps.detect_topics(q) or 'nothing'}")
    assert not misses, "student phrasings that find nothing:\n" + "\n".join(misses)


def test_ordinary_questions_still_pull_no_procedure():
    # Widening the triggers must not turn every question into paperwork.
    for q in [
        "what math courses are required for my major?",
        "where can I eat on campus?",
        "who is my adviser?",
        "what clubs should I join?",
        "when is the last day to drop?",   # a date question, not a procedure
        "how many credits do I need?",
        "I'm stressed about finals",
    ]:
        assert ps.find_procedures(q) == [], f"{q!r} pulled {ps.find_procedures(q)}"


def test_scope_words_separate_one_course_from_the_whole_term():
    # "get out of one class" and "get out of this semester" differ by scope
    # alone, and they lead to completely different paperwork.
    assert "late_drop" in ps.detect_topics("I want to get out of one class")
    assert "withdrawal" in ps.detect_topics("how do I get out of this semester entirely")


def test_students_words_find_the_procedure_not_just_the_policy_name():
    # A student who knows to say "grade forgiveness" always found it. One
    # describing what actually happened to them did not, and got an ungrounded
    # answer instead — the opposite of who needs help. Every phrasing below
    # returned nothing before the trigger list was widened.
    for q in [
        "I failed a course and retook it. Can the old grade be removed?",
        "I repeated a class, does the old grade still count?",
        "took it again — does the first grade go away?",
        "can I replace my grade from last term?",
    ]:
        assert "grades" in ps.detect_topics(q), f"{q!r} → {ps.detect_topics(q)}"
        assert ps.find_procedures(q), f"{q!r} found no procedure"


def test_a_plain_date_question_is_not_a_petition():
    # "When is the deadline" must NOT be turned into paperwork.
    assert ps.detect_topics("when is the late drop deadline?")[0] == "late_drop"
    assert "petition" not in ps.detect_topics("how do I drop a class?")


def test_unrelated_questions_match_nothing():
    for q in ["what math courses are required for my major?", "who is my adviser?", ""]:
        assert ps.find_procedures(q) == [], f"{q!r} should not pull a procedure"
        assert ps.build_procedures_snippet(q) == ""


def test_snippet_carries_steps_source_and_the_no_invention_rule():
    snippet = ps.build_procedures_snippet("I want to retroactively withdraw")
    assert snippet, "retroactive withdrawal must produce grounding"
    assert "Steps:" in snippet
    assert "https://" in snippet, "the student needs the source link"
    assert "Do NOT invent" in snippet, "this sends someone to file real paperwork"


def test_topic_coverage():
    # Each topic that has trigger phrases should have at least one procedure
    # behind it, or the triggers promise something the data cannot pay out.
    have = {p["topic"] for p in ps.load_procedures()}
    missing = [t for t in ps.TOPIC_TRIGGERS if t not in have]
    assert not missing, f"topics with triggers but no procedures: {missing}"


def test_sap_and_credit_overload_reach_the_student():
    """Two gaps found by testing ACE against real Reddit situations, where the
    community named the answer and ACE could not.

    A student losing federal aid got routed to the aid office with no idea what
    had happened to them; "satisfactory academic progress" existed nowhere in
    ACE. A student on academic warning was told an invented policy, because the
    19-credit rule existed nowhere either."""
    for q, want in [
        ("i got an email saying im not meeting academic requirements for financial aid", "aid_progress"),
        ("i lost my financial aid what do i do", "aid_progress"),
        ("can i appeal my financial aid", "aid_progress"),
        ("can i take more than 19 credits", "credit_overload"),
        ("im on academic warning can i still overload credits", "credit_overload"),
    ]:
        assert want in ps.detect_topics(q), f"{q!r} → {ps.detect_topics(q)}"
        assert ps.find_procedures(q), f"{q!r} found no procedure"


def test_the_sap_appeal_lists_are_not_inverted():
    """The single most dangerous extraction in the repo.

    The SAP page renders "Extenuating circumstances MAY include" and "NOT
    considered extenuating circumstances" side by side. Flattened, they merge —
    and the merged list reads as if time-management problems were valid grounds.
    They are explicitly refused, and an appeal cannot be re-filed on the same
    reason, so a student acting on the inverted list burns their one attempt.

    These were read off the rendered page by a human on 2026-08-27."""
    rec = next((p for p in ps.load_procedures() if p.get("verified_notes")
                and p["topic"] == "aid_progress"), None)
    assert rec, "the SAP record lost its verified notes"
    notes = " ".join(rec["verified_notes"]).lower()

    # The accepted side.
    assert "death of a loved one" in notes
    assert "diagnosed by a professional" in notes
    # The refused side, and it must be marked as refused.
    refused = next(n for n in rec["verified_notes"] if n.lower().startswith("not accepted"))
    for item in ["time management", "not understanding university policies",
                 "not being able to pay tuition"]:
        assert item in refused.lower(), f"{item!r} must sit on the NOT-accepted side"
    # The distinction that decides the appeal.
    assert "undiagnosed" in notes or "not diagnosed" in notes
    assert "same reason twice" in notes


def test_verified_facts_survive_the_block_substitution():
    """When a checklist renders, the itemised grounding is withheld — that is
    the point. But it was withholding the hand-verified facts too, so the
    credit-overload rule that decides the answer never reached the model and it
    answered from its own prior instead."""
    q = "im on academic warning, is there any way to overload credits?"
    recs = ps.find_procedures(q)
    facts = [n for r in recs for n in (r.get("verified_notes") or [])]
    assert facts, "the verified credit-overload rule is not reachable from this question"
    assert any("24 credits" in f for f in facts)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("\nall procedure checks passed")
