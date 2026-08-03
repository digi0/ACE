"""Self-check for the events dataset and its freshness guard.

Runs against the committed events.json — no network, no LLM.

    python -m backend.test_events
"""

import json
from datetime import date, timedelta

from backend.services import events_service as es


def test_dataset_is_present_and_shaped():
    data = es._load()
    assert data, "events.json should be built"
    assert data.get("scraped_at"), "an expiring dataset must record when it was taken"
    for e in data["events"][:40]:
        assert e["name"] and e["starts_on"], e
        assert e["url"].startswith("https://discover.psu.edu/event/"), e["url"]


def test_only_future_events_are_returned():
    today = date.today().isoformat()
    for e in es.upcoming_events():
        assert e["starts_on"][:10] >= today, f"{e['name']} already happened"


def test_windows_narrow_the_result():
    week = es.upcoming_events(within_days=7)
    month = es.upcoming_events(within_days=31)
    assert len(week) <= len(month), "a 7-day window cannot exceed a 31-day one"


def test_only_event_questions_get_events():
    assert es.mentions_events("what's happening on campus this week?")
    assert es.mentions_events("anything happening tonight?")
    assert not es.mentions_events("what math courses do I need?")
    assert es.build_events_snippet("what math courses do I need?") == ""


def test_a_stale_snapshot_refuses_to_name_events(monkeypatch=None):
    # The whole point of the guard: rather than announcing an event that already
    # happened, ACE must admit the list is old and hand over the live page.
    original = es.is_stale
    es.is_stale = lambda: True
    try:
        snippet = es.build_events_snippet("what's happening this week?")
        assert "OUT OF DATE" in snippet
        assert "Do NOT name or date any event" in snippet
        assert es.EVENTS_PAGE in snippet
    finally:
        es.is_stale = original


def test_staleness_is_driven_by_the_snapshot_date():
    age = es.snapshot_age_days()
    assert age is not None and age >= 0, "must be able to age the snapshot"
    assert age <= es.STALE_AFTER_DAYS or es.is_stale(), \
        "an old snapshot must report itself stale"


def test_snippet_carries_links_and_the_no_invention_rule():
    if es.is_stale():
        return  # covered by the stale test above
    snippet = es.build_events_snippet("what's happening on campus this week?")
    assert "discover.psu.edu/event/" in snippet, "each event needs its link"
    assert "Do NOT invent events" in snippet
    assert "complete list" in snippet, "must not imply this is everything"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("\nall event checks passed")
