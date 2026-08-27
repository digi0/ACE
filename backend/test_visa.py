"""Self-check for the F-1 provisions dataset and service.

This is the highest-stakes content in ACE. A wrong answer about money costs a
late fee; a wrong answer here costs someone their immigration status. So most of
these tests assert what ACE must NOT do.

    python -m backend.test_visa
"""

import json

from backend.services import visa_service as vs


def test_a_situation_finds_the_provisions_the_student_did_not_know_about():
    """The whole reason this dataset exists: a student about to drop a class has
    several authorised routes and knows about none of them."""
    for q, want in [
        ("I want to drop a class but I am on an F-1 visa", "reduced_course_load"),
        ("how many credits do I need to stay full time?", "full_time_enrollment"),
        ("can I do an unpaid internship over the summer?", "cpt"),
        ("when can I apply for OPT?", "opt"),
        ("my SEVIS record was terminated", "status_violation"),
        ("can I work on campus?", "on_campus_work"),
        ("do I need a travel signature to go home?", "travel"),
    ]:
        assert want in vs.detect_topics(q), f"{q!r} → {vs.detect_topics(q)}"
        assert vs.find_provisions(q), f"{q!r} found no provisions"


def test_every_provision_served_carries_its_risk():
    """A provision without its danger is the sentence that gets someone
    deported: "you can enrol in 6 credits" with no "dropping below full-time
    WITHOUT authorisation violates status the day it happens"."""
    snippet = vs.build_visa_snippet("I want to drop a class, I'm on an F-1")
    assert "RISK IF DONE WRONG" in snippet, "risk must reach the prompt"
    assert "ALWAYS pair a provision with its risk" in snippet

    served = vs.find_provisions("I want to drop a class, I'm on an F-1")
    missing = [r["id"] for r in served if not r.get("risk_if_wrong")]
    assert not missing, f"served with no risk stated: {missing}"


def test_ace_refuses_to_rule_on_the_student_s_own_case():
    """Only a DSO can determine eligibility or status. These all ask ACE to."""
    for q in ["am I eligible for CPT?", "do I qualify for OPT?",
              "is my status ok?", "should I file for OPT now?",
              "will I lose my visa if I drop this class?",
              "am I out of status?"]:
        assert vs.asks_for_determination(q), f"{q!r} is a determination request"

    # ...and the snippet must say so loudly rather than implying a yes.
    snippet = vs.build_visa_snippet("am I eligible for CPT?")
    assert "RULE ON THEIR OWN CASE" in snippet
    assert "Do not soften the refusal into an implied yes" in snippet


def test_asking_how_a_rule_works_is_not_asking_for_a_ruling():
    """The guard must not swallow the questions ACE exists to answer."""
    for q in ["what are the approved reasons for a reduced course load?",
              "how many credits is full time?",
              "what is CPT?",
              "when does the OPT application window open?"]:
        assert not vs.asks_for_determination(q), f"{q!r} is a rule question"


def test_the_prompt_forbids_inventing_numbers():
    snippet = vs.build_visa_snippet("how many credits do I need to stay full time?")
    assert "Quote the stated limits exactly as written" in snippet
    assert "never fill a gap" in snippet
    assert "Never tell the student they qualify" in snippet


def test_the_office_is_issa_not_dissa():
    """ACE called it "DISSA (Directorate of International Student & Scholar
    Advising)". Penn State Global's own pages say ISSA, 12 times across the
    scrape. Sending someone to a wrong office name is the same defect class as
    the petitions record that pointed at the Office of Student Aid."""
    snippet = vs.build_visa_snippet("can I work on campus?")
    assert "ISSA" in snippet and "Do not call it DISSA" in snippet

    from backend.services.chat_service import INTERNATIONAL_RESOURCES_SNIPPET
    assert "ISSA" in INTERNATIONAL_RESOURCES_SNIPPET
    assert "Directorate of International" not in INTERNATIONAL_RESOURCES_SNIPPET


def test_a_stale_snapshot_withholds_the_numbers_but_keeps_the_map():
    """Immigration figures move. Unlike events, going stale must not blank the
    answer — the provisions still exist, only the numbers stop being current."""
    real_age = vs.snapshot_age_days
    try:
        vs.snapshot_age_days = lambda: vs.STALE_AFTER_DAYS + 1
        snippet = vs.build_visa_snippet("how many credits do I need to stay full time?")
        assert "do NOT state any specific number" in snippet
        assert "F-1 PROVISIONS" in snippet, "the map must survive staleness"
    finally:
        vs.snapshot_age_days = real_age


def test_unrelated_questions_get_nothing():
    for q in ["what math courses are required for my major?",
              "when is the drop deadline?", "where can I eat on campus?", ""]:
        assert vs.find_provisions(q) == [], f"{q!r} pulled visa provisions"
        assert vs.build_visa_snippet(q) == ""


def test_the_dataset_itself_is_sound():
    data = json.loads(vs.VISA_FILE.read_text(encoding="utf-8"))
    recs = data["records"]
    assert len(recs) >= 25, f"only {len(recs)} provisions"
    assert data["count"] == len(recs)
    assert not data["sources_failed"], f"sources failed: {data['sources_failed']}"

    # Every record must be traceable back to the page it came from — this is the
    # one dataset where an unsourced claim is unacceptable.
    for r in recs:
        assert r["source_url"].startswith("https://global.psu.edu/"), r["id"]
        assert r["what_it_is"], r["id"]
        assert r["visa"] == "F-1"

    # No staff names — same rule the procedures dataset learned the hard way.
    # Word boundaries, because "problems." contains "ms." and this check failed
    # on its first run for exactly the reason half of today's real bugs did.
    import re as _re
    blob = json.dumps(recs)
    for honorific in ["Mr", "Mrs", "Ms", "Dr", "Prof"]:
        hit = _re.search(rf"\b{honorific}\.\s+[A-Z]", blob)
        assert not hit, f"a personal name may have leaked: {hit.group(0)!r}"


def test_the_verdict_carries_its_own_condition():
    """"i want to drop a class but im on an f1 visa" opened with "You can drop a
    class while on an F-1 visa". Everything after it was right; that clause is
    the one a frightened student acts on, and the caveat arrives too late.

    The answer contract demands a verdict in the opening line. On this content
    the safe verdict is almost never a bare yes, so the condition has to ride
    inside it."""
    snippet = vs.build_visa_snippet("i want to drop a class but im on an f1 visa")
    assert "THE FIRST SENTENCE CARRIES THE CONDITION" in snippet
    assert "Not without authorisation first" in snippet
    assert "arrives too late" in snippet


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("\nall visa checks passed")
