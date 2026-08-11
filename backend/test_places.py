"""Self-check for the campus places dataset and matcher.

Runs against the committed places.json — no network, no LLM.

    python -m backend.test_places
"""

import re

from backend.services import places_service as ps


def test_dataset_is_present_and_shaped():
    places = ps.load_places()
    assert len(places) >= 30, f"expected a real campus dataset, got {len(places)}"
    for p in places:
        assert p["name"], "every place needs a name"
        assert p["category"] in ps.CATEGORY_TRIGGERS, f"{p['name']}: {p['category']}"
        assert p["what_it_is"], f"{p['name']} has no description"
        assert p["map_url"].startswith("https://www.google.com/maps/"), p["map_url"]


def test_hours_are_never_stored_as_values():
    # The whole design rests on this: dining and library hours change by term and
    # by day, so a stored time is a confidently wrong answer that sends a student
    # across campus for nothing. Records carry the live hours PAGE instead.
    clock = re.compile(r"\b\d{1,2}\s*(:\d{2})?\s*(am|pm|a\.m\.|p\.m\.)", re.I)
    for p in ps.load_places():
        for field in ("what_it_is", "where"):
            assert not clock.search(p.get(field, "")), \
                f"{p['name']} stored an opening time in {field}: {p[field]!r}"
        assert "hours" not in p or isinstance(p.get("hours_url"), str)


def test_questions_route_to_the_right_part_of_campus():
    cases = [
        ("where can I get food late at night?", "dining"),
        ("where should I study tonight?", "study_space"),
        ("is there a gym on campus?", "recreation"),
        ("where do I park my car?", "parking"),
        ("how do I print something?", "it_printing"),
        ("what are my housing options?", "housing"),
    ]
    for question, expected in cases:
        got = ps.detect_categories(question)
        assert got and got[0] == expected, f"{question!r} → {got}, wanted {expected}"


def test_student_phrasing_finds_the_right_part_of_campus():
    # Written the way a student types, not the way a directory is indexed.
    # "I'm starving" and "somewhere quiet to cram" both matched nothing before.
    for q, want in [
        ("I'm starving, where do I go", "dining"),
        ("somewhere quiet to cram", "study_space"),
        ("where can I do laundry", "housing"),
        ("I need to see a doctor", "health"),
        ("how do I get to campus without a car", "transit"),
        ("my laptop broke, who fixes it", "it_printing"),
        ("where do I work out", "recreation"),
        ("got a ticket on my windshield", "parking"),
    ]:
        assert want in ps.detect_categories(q), f"{q!r} → {ps.detect_categories(q)}"


def test_the_question_reaches_the_record_that_answers_it():
    """Every one of these opened on the wrong record, and for two reasons.

    A question can name a category and nothing inside it — "I need to see a
    doctor" matches no health record by name, so all eight scored zero and file
    order won, which put Lactation Rooms first. Hence `primary` in places.json.

    And when the question DID name the service, word forms lost it: "prescription"
    never matched "Fill prescriptions", "rehab" never matched "rehabilitation",
    and "x-ray" was split into "x" and "ray" and dropped for being too short.
    """
    for q, want in [
        ("I need to see a doctor", "University Health Services (UHS)"),
        ("where can I get a prescription", "Pharmacy"),
        ("I need an x-ray", "Radiology"),
        ("where do I get blood work done", "Laboratory"),
        ("is there an ambulance on campus", "Emergency Medical Services (EMS)"),
        ("I hurt my knee and need rehab", "Physical Therapy"),
        ("where can I get emotional support", "Counseling and Psychological Services (CAPS)"),
        ("where do I work out", "Campus Recreation"),
        ("where do I park my car", "Student Parking"),
    ]:
        got = [p["name"] for p in ps.find_places(q)]
        assert got[:1] == [want], f"{q!r} → {got[:3]}, wanted {want}"


def test_grammar_does_not_outvote_meaning():
    """CAPS beat Physical Therapy on "I hurt my knee and need rehab" because it
    has the longer paragraph, so it contained "and" and "need" more often. The
    stop-word list existed but was only applied to the fallback path."""
    q = "I hurt my knee and need rehab"
    assert not (ps._words(q) & {"and", "need"}), "grammar must not score"
    scores = {p["name"]: ps._relevance(p, q) for p in ps.load_places()
              if p["category"] == "health"}
    assert scores["Physical Therapy"] > scores[
        "Counseling and Psychological Services (CAPS)"]


def test_a_category_front_door_is_only_claimed_where_one_exists():
    """`primary` marks the record to name first when the question picks a
    category but nothing in it. Peer lists — dining, housing, libraries — have no
    front door, and flagging one would be an editorial opinion posing as data."""
    by_cat = {}
    for p in ps.load_places():
        if p.get("primary"):
            by_cat.setdefault(p["category"], []).append(p["name"])
    assert all(len(v) == 1 for v in by_cat.values()), f"two front doors: {by_cat}"
    assert set(by_cat) == {"health", "recreation", "transit", "parking"}, by_cat
    for peer in ("dining", "housing", "library", "study_space", "it_printing"):
        assert peer not in by_cat, f"{peer} is a peer list, not a hierarchy"


def test_a_short_trigger_cannot_hide_inside_a_word():
    """The failure the intent router was fixed for, which never reached here.

    Triggers were matched as bare substrings, so "tow" lived in "toward" and
    "eat" lived in create, theater, repeated, great, heat and reseat. "do my AP
    credits count toward my degree?" came back with six parking cards.
    """
    for q in [
        "do my AP credits count toward my degree?",
        "does my minor count toward electives?",
        "how do I create a study plan?",
        "what does the theater major require?",
        "I repeated a course, does it replace the grade?",
        "is there great advice for freshmen?",
        "can I reseat an exam?",
        "how do I heat up my schedule with harder classes?",
    ]:
        assert ps.detect_categories(q) == [], f"{q!r} → {ps.detect_categories(q)}"


def test_a_real_word_in_an_academic_question_is_still_not_a_place():
    """Word boundaries do not save these — the word is genuinely there, used to
    talk about a degree. A real place question either says so in a phrase or
    names the place; a lone short word next to "major" or "class" is coincidence."""
    for q in [
        "I am sick of my major, can I switch?",
        "who teaches the gym class requirement?",
        "does the bus schedule affect my class times?",
        "how do I print my transcript?",
    ]:
        assert ps.detect_categories(q) == [], f"{q!r} → {ps.detect_categories(q)}"

    # ...while the same words still work when the question really is about campus.
    for q, want in [("where do I work out at the gym", "recreation"),
                    ("how do I take the bus to campus", "transit"),
                    ("I feel sick, where do I go", "health"),
                    ("how do I print something?", "it_printing")]:
        assert want in ps.detect_categories(q), f"{q!r} → {ps.detect_categories(q)}"


def test_somewhere_else_is_not_our_campus():
    """"Where should I eat in New York?" was answered with six Penn State dining
    halls, because "eat" is a dining trigger and nothing read the rest of the
    sentence. The list is a NOT-us list rather than a place-name list, because
    Penn State is also Abington, Altoona and twenty-two others."""
    for q in ["whats the best place to eat in new york city", "best restaurants in chicago",
              "where should I eat in london", "how do I get to NYU",
              "is Harvard better than Penn State"]:
        assert ps.detect_categories(q) == [], f"{q!r} → {ps.detect_categories(q)}"
    # Our own campuses are not "elsewhere".
    assert "dining" in ps.detect_categories("where can I eat at Altoona")


def test_a_product_recommendation_is_never_a_campus_question():
    """"What's the best laptop to buy?" rendered the campus IT desks, because
    "laptop" is an it_printing trigger. Penn State does not sell you a laptop."""
    for q in ["what's the best laptop to buy in 2026", "cheapest phone deal",
              "recommend me a good computer", "which tablet is worth buying"]:
        assert ps.detect_categories(q) == [], f"{q!r} → {ps.detect_categories(q)}"
    # Narrow on purpose: buying a permit really is a campus question.
    assert "parking" in ps.detect_categories("where do I buy a parking permit")
    assert "it_printing" in ps.detect_categories("my laptop broke, who fixes it")


def test_unrelated_questions_match_nothing():
    for q in ["what math courses are required for my major?", "when is the drop deadline?", ""]:
        assert ps.find_places(q) == [], f"{q!r} should not pull a campus place"
        assert ps.build_places_snippet(q) == ""


def test_snippet_carries_directions_and_forbids_stating_hours():
    snippet = ps.build_places_snippet("where can I eat on campus?")
    assert snippet, "a dining question must produce grounding"
    assert "google.com/maps" in snippet, "directions links are the ask"
    assert "Live hours:" in snippet, "must hand over the live hours page"
    assert "Never state a time" in snippet, "must forbid inventing hours"


def test_category_coverage():
    have = {p["category"] for p in ps.load_places()}
    # Triggers that can never pay out are a promise the dataset does not keep.
    missing = [c for c in ps.CATEGORY_TRIGGERS if c not in have]
    assert len(missing) <= 1, f"too many categories with triggers but no data: {missing}"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("\nall places checks passed")
