"""Self-check for the student-account dataset and the advice boundary.

The boundary is the point of this suite. ACE answering "who do I email about
this charge" is the product; ACE answering "should I take this loan" is a
liability. Both are money questions and they look alike.

    python -m backend.test_money
"""

from backend.services import money_service as ms


def test_dataset_is_present_and_shaped():
    records = ms.load_money()
    assert len(records) >= 10, f"expected the bursar set, got {len(records)}"
    for r in records:
        assert r["title"], "every record needs a title"
        assert r["topic"] in ms.TOPIC_TRIGGERS, f"{r['title']}: {r['topic']}"
        assert r["source_url"].startswith("https://"), r["source_url"]
        assert r.get("what_it_is") or r.get("steps"), f"{r['title']} is empty"


def test_navigational_questions_are_answered():
    for q in [
        "Who do I email about a charge on my student account?",
        "why have I not received my refund?",
        "what happens if I miss the tuition due date?",
        "how do I pay my bill?",
    ]:
        assert ms.find_money(q), f"{q!r} should find navigation records"
        assert ms.build_money_snippet(q), f"{q!r} should produce grounding"


def test_student_phrasing_finds_the_navigation():
    # Only one of these six matched before — the triggers were written in the
    # bursar's words, not a student's.
    for q, want in [
        ("there's a weird charge I don't recognise", "billing"),
        ("who do I ask about money I'm owed", "refunds"),
        ("I can't pay by the due date", "late_fees"),
        ("my account is on hold for money", "late_fees"),
        ("how do I set up a payment plan", "payments"),
        ("my parents want to pay my tuition", "payments"),
    ]:
        assert want in ms.detect_topics(q), f"{q!r} → {ms.detect_topics(q)}"


def test_asking_who_to_contact_is_not_automatically_a_billing_question():
    """"who do i contact" sat in the contacts trigger list with no money in it,
    so "who do I contact about my transcript" and "who do I contact about my
    grade appeal" both came back grounded in bursar records — the billing office
    attached to a registrar question."""
    for q in ["who do I contact about my transcript",
              "who do I contact about my grade appeal",
              "who do I email about changing my major",
              "who handles course substitutions"]:
        assert ms.detect_topics(q) == [], f"{q!r} → {ms.detect_topics(q)}"

    # ...but the same phrasing with money in it still is one.
    for q in ["who do I email about a charge on my account",
              "who do I contact about my tuition bill",
              "who do I talk to about my bill"]:
        assert ms.detect_topics(q), f"{q!r} should still reach the money records"


def test_short_money_words_do_not_hide_inside_ordinary_ones():
    """"aid" lives in afraid, said, paid and maid; "bill" in billion; "grant" in
    granted. Without boundaries "I'm afraid of failing" counted as money."""
    for q in ["I'm afraid I should drop this class",
              "she said I should take it", "granted admission to honors"]:
        assert not ms.asks_for_advice(q), f"{q!r} is not a money decision"
    for q in ["should I take out a loan to cover this?",
              "can I afford to stay another semester?"]:
        assert ms.asks_for_advice(q), f"{q!r} is a money decision"


def test_advice_questions_are_refused_even_with_no_data_match():
    # The dangerous case: a pure advice question matches no navigational topic,
    # so without an explicit guard it would sail through with no boundary at all.
    for q in [
        "should I take out a loan to cover this?",
        "can I afford to stay another semester?",
        "how much aid will I get?",
    ]:
        assert ms.asks_for_advice(q), f"{q!r} should read as advice"
        snippet = ms.build_money_snippet(q)
        assert "OUT OF SCOPE" in snippet or "Student Aid" in snippet, \
            f"{q!r} produced no guardrail"


def test_the_advice_guard_does_not_leak_into_course_questions():
    # "should i take" is an advice marker AND the normal way to ask about a
    # course. Money context is what separates them.
    for q in [
        "should I take CMPSC 121 next semester?",
        "should I take 15 or 18 credits?",
        "what math courses are required?",
    ]:
        assert not ms.asks_for_advice(q), f"{q!r} wrongly flagged as money advice"
        assert ms.build_money_snippet(q) == "", f"{q!r} pulled a money snippet"


def test_snippet_states_ace_cannot_see_the_account():
    snippet = ms.build_money_snippet("why have I not received my refund?")
    assert "do NOT have access" in snippet or "cannot see" in snippet, \
        "ACE must never imply it can see the student's balance"
    assert "Student Aid" in snippet, "aid advice must be routed out"
    assert "never estimate" in snippet or "Do not invent" in snippet


def test_unrelated_questions_match_nothing():
    for q in ["when is the drop deadline?", "where can I eat?", ""]:
        assert ms.find_money(q) == []
        assert ms.build_money_snippet(q) == ""


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("\nall money checks passed")
