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
