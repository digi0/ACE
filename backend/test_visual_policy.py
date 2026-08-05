"""Self-check for the visual policy.

The failure this guards against is enthusiasm: turning every answer into a
planner spread because the machinery exists. Most cases below assert that
NOTHING renders.

    python -m backend.test_visual_policy
"""

from backend.services import visual_policy as vp


def lvl(q, intent, **kw):
    return vp.decide(q, intent, **kw)


def test_most_answers_stay_prose():
    # The common case. Plenty of data available, no structure worth drawing.
    # Levels 0 and 1 are BOTH prose — level 1 just gives one date or number
    # weight inside the sentence. What must not happen is a block rendering.
    cases = [
        ("who do I email about a charge?", "contact", {"cards": 4}),
        ("when is the last day to drop?", "deadline", {"strip": 1}),
        ("what is a registration hold?", "logistics", {"checklist": 1}),
        ("how many credits is CMPSC 465?", "courses", {"cards": 1}),
    ]
    for q, intent, counts in cases:
        d = lvl(q, intent, counts=counts)
        assert d["level"] <= 1, f"{q!r} → level {d['level']} ({d['reason']})"
        assert d["block"] is None, f"{q!r} rendered a {d['block']} block"
        assert not d["offer"], f"{q!r} should not even offer"


def test_distress_and_referral_questions_never_get_a_visual():
    # A student in crisis does not need an infographic, and a diagram lends
    # unearned authority to a question ACE is deliberately refusing to answer.
    for intent in vp.NEVER_VISUAL_INTENTS:
        d = lvl("I'm overwhelmed and behind on everything", intent,
                counts={"plan": 6, "strip": 5, "cards": 8}, has_audit=True)
        assert d["level"] == 0 and not d["offer"], f"{intent} produced {d}"
        assert "prose-only" in d["reason"]


def test_prereq_branching_is_the_strongest_case():
    d = lvl("Can I take CMPSC 465 next fall?", "courses", counts={"map": 6})
    assert d["level"] == 2 and d["block"] == "map", d


def test_asking_to_see_it_escalates_to_full():
    d = lvl("Show me what CMPSC 465 unlocks", "courses", counts={"map": 6})
    assert d["level"] == 3 and d["block"] == "map", d

    d = lvl("lay out my next two terms", "recommendation",
            counts={"plan": 8}, has_audit=True)
    assert d["level"] == 3 and d["block"] == "plan", d


def test_asking_for_brevity_outranks_everything_but_the_floor():
    d = lvl("just tell me quickly what I should take", "recommendation",
            counts={"plan": 8}, has_audit=True)
    assert d["level"] == 0 and not d["offer"], d


def test_too_little_data_means_no_block():
    # One course is not a planner; two dates are not a timeline.
    assert lvl("what should I take?", "recommendation",
               counts={"plan": 1}, has_audit=True)["level"] < 2
    assert lvl("what's coming up?", "deadline", counts={"strip": 2})["level"] < 2


def test_too_much_data_becomes_an_offer_not_a_dump():
    d = lvl("what are all my remaining requirements?", "student_progress",
            counts={"plan": 40}, has_audit=True)
    assert d["offer"] is True and d["level"] == 0, d
    assert "exceeds" in d["reason"]
    assert vp.offer_line("plan")


def test_a_personal_plan_needs_a_real_record():
    d = lvl("what should I take next semester?", "recommendation", counts={"plan": 5})
    assert d["offer"] and d["level"] == 0, "no audit → offer, don't fabricate a plan"
    d = lvl("what should I take next semester?", "recommendation",
            counts={"plan": 5}, has_audit=True)
    assert d["level"] == 2 and d["block"] == "plan", d


def test_never_draws_from_data_that_does_not_exist():
    d = lvl("show me a chart of my progress", "student_progress", counts={})
    assert d["level"] == 0 and d["block"] is None, "asked, but nothing to draw"
    assert "no structured data" in d["reason"]


def test_every_decision_explains_itself():
    for q, intent, counts in [
        ("can I take CMPSC 465?", "courses", {"map": 4}),
        ("when is the deadline?", "deadline", {"strip": 1}),
        ("plan my terms", "recommendation", {"plan": 6}),
    ]:
        assert lvl(q, intent, counts=counts, has_audit=True)["reason"], "must be explainable"


def test_directive_matches_the_decision():
    d0 = vp.build_visual_directive("who do I email?", "contact")
    assert "answer in prose" in d0.lower()
    # The policy governs STRUCTURE, not length. A directive that suppresses
    # detail is how a gen-ed answer loses its per-course explanation.
    assert "detail the question deserves" in d0

    d2 = vp.build_visual_directive("can I take CMPSC 465?", "courses", {"map": 5})
    assert "compact map" in d2 and "what each one means" in d2

    d3 = vp.build_visual_directive("show me the map for CMPSC 465", "courses", {"map": 5})
    assert "full map" in d3

    off = vp.build_visual_directive("what are all my requirements?", "student_progress",
                                    {"plan": 40}, has_audit=True)
    assert "exactly one short offer" in off and "Want me to" in off


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("\nall visual-policy checks passed")
