"""Self-check for the student-organisation dataset and matcher.

Runs against the committed clubs.json — no network, no LLM.

    python -m backend.test_clubs
"""

from backend.services import clubs_service as cs


def test_dataset_is_present_and_shaped():
    clubs = cs.load_clubs()
    assert len(clubs) > 500, f"expected the full directory, got {len(clubs)}"
    for club in clubs[:50]:
        assert club["name"], "every organisation needs a name"
        assert club["url"].startswith("https://discover.psu.edu/organization/"), club["url"]
    assert any(c.get("instagram") for c in clubs), "links are the point of this dataset"


def test_no_personal_contact_emails_are_stored():
    # Engage exposes a named student's @psu.edu address as the org contact. It is
    # deliberately not scraped — ACE quotes this file into answers.
    for club in cs.load_clubs():
        assert "email" not in club, f"{club['name']} carries a contact email"


def test_interest_matching_finds_the_obvious_things():
    names = " | ".join(c["name"].lower() for c in cs.search_clubs(["dancing"]))
    assert "dance" in names, f"dancing should surface dance orgs, got: {names}"

    climbing = cs.search_clubs(["rock climbing"])
    assert climbing and "climb" in climbing[0]["name"].lower()


def test_partial_word_matches_do_not_win():
    # "Adult Learner Programs" shares the stem "learn" with "machine learning".
    # Scoring each phrase by how much of it landed is what keeps it out.
    names = [c["name"].lower() for c in cs.search_clubs(["machine learning"])]
    assert names, "a real match exists and must be found"
    assert not any("adult learner" in n for n in names), names


def test_no_match_returns_nothing_rather_than_a_near_miss():
    assert cs.search_clubs(["quidditch unicorn wizardry"]) == []
    assert cs.search_clubs([]) == []
    assert cs.search_clubs(["the and of"]) == [], "stopwords alone are not an interest"


def test_snippet_is_empty_when_nothing_matches():
    # The career bracket's refusal ("do not name clubs") depends on this: no
    # grounding block means ACE must not start inventing organisations again.
    assert cs.build_clubs_snippet(["quidditch unicorn wizardry"]) == ""
    assert cs.build_clubs_snippet([], question="") == ""


def test_snippet_carries_links_and_the_no_invention_rule():
    snippet = cs.build_clubs_snippet(["dancing"])
    assert "discover.psu.edu/organization/" in snippet, "profile links must be present"
    assert "instagram.com" in snippet.lower(), "Instagram links are the ask"
    assert "Do NOT invent" in snippet


def test_question_is_used_when_the_profile_is_empty():
    # A student can ask about dance without ACE having learned that they dance.
    snippet = cs.build_clubs_snippet(None, question="are there any dance clubs here?")
    assert "dance" in snippet.lower(), "must fall back to the question's own words"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("\nall clubs checks passed")
