"""Self-check for the extracted handbook policies and their relay.

Run: python -m backend.test_policies
"""
from backend.data.policy_extractor import TOPICS, dedupe
from backend.services.policy_service import (
    INTENT_TOPICS,
    build_policy_snippet,
    load_policies,
    policy_sources,
)


def test_policies_file():
    data = load_policies()
    policies = data["policies"]
    assert policies, "policies.json is empty — run python -m backend.data.policy_extractor"
    assert len(policies) == data["policy_count"]

    ids = set()
    for p in policies:
        assert p["scope"] in ("cs", "ds"), p
        assert p["topic"] in TOPICS, p
        assert p["statement"].strip(), p
        assert p["source"]["link"].startswith("https://"), p
        assert p["source"]["pages"], p          # every policy is traceable to a page
        assert p["policy_id"] not in ids, f"duplicate id {p['policy_id']}"
        ids.add(p["policy_id"])

    # Both handbooks must be represented, and the rules students ask about most.
    assert {p["scope"] for p in policies} == {"cs", "ds"}
    for scope in ("cs", "ds"):
        topics = {p["topic"] for p in policies if p["scope"] == scope}
        assert "etm" in topics, f"{scope}: no Entrance-to-Major policy extracted"
        assert {"petition", "substitution"} & topics, f"{scope}: no petition/substitution policy"


def test_dedupe_merges_pages():
    a = {"scope": "cs", "topic": "etm", "title": "Entrance to Major",
         "statement": "short", "details": [], "courses": [], "source": {"pages": [6]}}
    b = {"scope": "cs", "topic": "etm", "title": "entrance to major!",
         "statement": "a much longer statement", "details": ["x"], "courses": [], "source": {"pages": [7]}}
    out = dedupe([a, b])
    assert len(out) == 1
    assert out[0]["source"]["pages"] == [6, 7]
    assert out[0]["statement"] == "a much longer statement"


def test_snippet_relay():
    # CS/DS get policies; every other major must get nothing.
    for intent in INTENT_TOPICS:
        for scope in ("cs", "ds"):
            snippet = build_policy_snippet(intent, scope)
            if snippet:
                assert "DEPARTMENT HANDBOOK POLICIES" in snippet
                assert "Source:" in snippet
        assert build_policy_snippet(intent, "other") == ""
        assert build_policy_snippet(intent, None) == ""

    assert build_policy_snippet("etm", "cs"), "ETM questions must relay a policy"
    assert build_policy_snippet("wellbeing", "cs") == ""   # unmapped intent stays quiet
    assert policy_sources("cs") and not policy_sources("other")


if __name__ == "__main__":
    test_policies_file()
    test_dedupe_merges_pages()
    test_snippet_relay()
    print("policy self-check OK")
