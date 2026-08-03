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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("\nall procedure checks passed")
