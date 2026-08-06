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

    # A block with a renderer tells the model to stand back; one without tells it
    # to write the items out, because otherwise they reach the student nowhere.
    d2 = vp.build_visual_directive("can I take CMPSC 465?", "courses", {"map": 5})
    assert "rendered beneath" in d2 and "Do NOT reproduce" in d2
    # The noun has to match the block. Told "every item", a checklist answer
    # numbered all four petition steps out anyway — it did not read its steps as
    # the "items" it was being told to leave alone.
    assert "Every course" in d2
    assert "Every step" in vp.build_visual_directive(
        "how do I withdraw?", "logistics", {"checklist": 4})

    # Naming the items is an instruction the PROSE branches carry and the
    # rendered branches must not — that split is the whole fix for the answer
    # that listed six dining halls and then drew the same six as cards.
    assert "name them and include the links" in d0
    assert "name them and include the links" not in d2

    # Every block the policy can choose now has a renderer, so the directive
    # tells the model to stand back for all of them. The unrendered branch stays
    # in place for the next block type added ahead of its component.
    for block in ("map", "cards", "checklist", "strip", "plan"):
        assert block in vp.RENDERED_BLOCKS

    d3 = vp.build_visual_directive("show me the map for CMPSC 465", "courses", {"map": 5})
    assert "rendered beneath" in d3

    off = vp.build_visual_directive("what are all my requirements?", "student_progress",
                                    {"plan": 40}, has_audit=True)
    assert "exactly one short offer" in off and "Want me to" in off


def test_grounding_snippets_do_not_give_presentation_orders():
    """The bug this pins: "where can I eat on campus?" answered with six numbered
    places and their links, and then rendered the same six as cards.

    build_places_snippet ended with "Name these places ... and give the directions
    link" — written when every answer was prose. Once a block rendered underneath,
    the model held two contradictory orders and obeyed the more specific one. Only
    build_visual_directive decides how items reach the student now; a snippet says
    what is true and what may not be claimed, and stops there."""
    from backend.services.places_service import build_places_snippet
    from backend.services.clubs_service import build_clubs_snippet
    from backend.services.procedures_service import build_procedures_snippet

    banned = ("name these", "name them", "give the directions link",
              "include the links", "walk the student through")
    for label, snippet in [
        ("places", build_places_snippet("where can I eat on campus?")),
        ("clubs", build_clubs_snippet(None, question="what clubs are there for hiking?")),
        ("procedures", build_procedures_snippet("how do I retroactively withdraw?")),
    ]:
        assert snippet, f"{label} produced no grounding to check"
        low = snippet.lower()
        for phrase in banned:
            assert phrase not in low, f"{label} snippet still orders presentation: {phrase!r}"
        # ...while the grounding it exists for survives.
        assert "do not invent" in low or "not invent" in low, f"{label} lost its guard"


def test_a_rendered_block_withholds_its_items_from_the_prompt():
    """Instruction alone did not hold. "A block is rendered, do not repeat the
    items" was in the directive while the full itemised list was ALSO in the
    grounding, and the same dining question came back as six bullets on one run
    and two clean sentences on the next. The model cannot transcribe what it was
    never handed, so the list is withheld rather than discouraged."""
    from backend.services import blocks as B
    from backend.services.places_service import find_places
    from backend.services.procedures_service import find_procedures

    places = find_places("where can I eat on campus?")
    cards = B.places_cards(places)
    summary = B.grounding_summary("cards", cards)

    assert summary, "a rendered block must still ground the answer"
    for item in cards["items"]:
        assert item["title"] not in summary, \
            f"{item['title']!r} leaked into the prompt; the model will list it"
    assert str(len(cards["items"])) in summary, "prose still needs the count"
    assert "campus locations" in summary
    assert cards["hours_url"] in summary, "the one shared link must survive"

    checklist = B.procedure_checklist(find_procedures("how do I retroactively withdraw?"))
    csum = B.grounding_summary("checklist", checklist)
    for step in checklist["steps"]:
        assert step not in csum, "the steps are the block's job"
    # ...but what the student ACTS on stays: the office, the timing, the link,
    # and enough context that the model does not invent qualifying grounds.
    assert checklist["source"] in csum
    assert any(f["v"] in csum for f in checklist["facts"]), "facts must survive"
    assert checklist["what_it_is"] in csum

    assert B.grounding_summary("cards", None) == ""


def test_declining_the_strip_does_not_decline_the_answer():
    """"I missed the late drop deadline, what now?" routes to `deadline`, which
    claims the strip; the one-date guard then declines it and used to return —
    so the four-step petition checklist sitting right there never got a look in.
    Declining a block has to mean "keep looking", not "give up"."""
    q = "I missed the late drop deadline, what now?"
    d = lvl(q, "deadline", counts={"strip": 5, "checklist": 4})
    assert d["block"] == "checklist" and d["level"] == 2, d

    # With nothing else to show, one date still beats a term timeline.
    d = lvl(q, "deadline", counts={"strip": 5})
    assert d["block"] is None and d["level"] == 1, d


def test_a_course_that_opens_things_is_worth_drawing():
    """CMPSC 360 has no prerequisites and unlocks six. The counter only counted
    prerequisites, so "show me what CMPSC 360 unlocks" — a direct request, for
    precisely the shape the map exists to draw — rendered nothing."""
    from backend.services.chat_service import _count_visual_material

    counts = _count_visual_material("show me what CMPSC 360 unlocks", "courses",
                                    "Computer Science, B.S. (Engineering)", {})
    assert counts.get("map"), f"a course with 6 unlocks must be drawable, got {counts}"
    assert lvl("show me what CMPSC 360 unlocks", "courses",
               counts=counts)["block"] == "map"


def test_every_block_type_withholds_its_own_items():
    """The duplication was closed for cards and checklist first, and the other
    three kept doing it — which is why it still showed up in almost every answer.
    A map recited its own prerequisites; a plan listed every course it drew."""
    from backend.services import blocks as B

    graph = {"target": {"code": "CMPSC 465", "title": "Algorithms"},
             "groups": [[{"code": "CMPSC 122", "done": True},
                         {"code": "CMPSC 132", "done": False}],
                        [{"code": "CMPSC 360", "in_progress": True}]],
             "unlocks": [{"code": "CMPSC 465W"}], "has_record": True,
             "eligible": False, "on_track": True}
    m = B.grounding_summary("map", graph)
    assert "on track" in m, "the verdict IS the answer and must survive"
    assert "CMPSC 360" in m, "the one course in play is worth naming"
    assert "CMPSC 122" not in m, "a satisfied prerequisite is the map's job"
    assert "CMPSC 465W" not in m, "what it unlocks is the map's job"

    # No audit: the map states the requirement, the prose must not personalise it.
    blind = B.grounding_summary("map", {**graph, "has_record": False})
    assert "can or cannot" in blind
    assert "CMPSC 360" not in blind, "no record means no claim about this student"

    plan = B.grounding_summary("plan", {
        "terms": [{"label": "Next Term", "total": 15, "courses": [
            {"code": "PSYCH 100"}, {"code": "ENGL 15"}, {"code": "LA 83"}]}],
        "personalised": True})
    assert "3 courses" in plan and "15 credits" in plan
    for code in ("PSYCH 100", "ENGL 15", "LA 83"):
        assert code not in plan, f"{code} leaked; the plan draws it"


def test_a_meal_plan_is_not_somewhere_you_can_walk_to():
    from backend.services.blocks import places_cards
    from backend.services.places_service import find_places, _relevance

    places = find_places("where can I eat on campus?")
    assert places, "the dining question must still find dining"
    # "campus" is in the question and in the name, and that alone put a meal
    # plan above every actual dining hall.
    assert _relevance({"name": "Campus Meal Plan", "good_for": []},
                      "where can I eat on campus?") == 0

    cards = places_cards(places)
    for item in cards["items"]:
        if "Meal Plan" in item["title"]:
            assert not any(l["label"] == "directions" for l in item["links"]), \
                "a meal plan has no address; its directions link lands nowhere"
        assert not item["body"].endswith(" loca"), "clipped mid-word"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("\nall visual-policy checks passed")
