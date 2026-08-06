"""What's on this week — the question that makes ACE a Tuesday habit.

This is the only ACE dataset with an expiry date. Programs and procedures stay
true for a year; an events snapshot is wrong within weeks. So every read is
filtered against today, and when the snapshot runs dry ACE says so and hands over
the live page rather than announcing an event that already happened.

That guard is the same one _build_deadlines_snippet applies to the academic
calendar, for the same reason: a confidently stated stale date is worse than an
admitted gap.
"""

import json
import logging
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

EVENTS_FILE = Path(__file__).parent.parent / "data" / "events.json"
EVENTS_PAGE = "https://discover.psu.edu/events"
MAX_EVENTS = 6
# Past this, the snapshot is treated as untrustworthy even if rows remain.
STALE_AFTER_DAYS = 21

TRIGGERS = [
    "event", "events", "what's happening", "whats happening", "going on",
    "this week", "this weekend", "tonight", "today", "tomorrow",
    "something to do", "things to do", "anything happening",
    "meeting", "workshop", "fair", "info session", "social", "party",
    "performance", "concert", "game night", "speaker",
]

_STOPWORDS = {
    "event", "events", "campus", "penn", "state", "university", "park",
    "what", "whats", "happening", "going", "this", "week", "weekend", "the",
    "any", "there", "something", "things", "todo", "and", "for", "with",
    "tonight", "today", "tomorrow", "are", "some", "good", "how", "can",
}


@lru_cache(maxsize=1)
def _load() -> dict:
    if not EVENTS_FILE.exists():
        logger.warning("events.json missing at %s", EVENTS_FILE)
        return {}
    try:
        return json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.error("events.json unreadable: %s", exc)
        return {}


def snapshot_age_days() -> int | None:
    scraped = (_load().get("scraped_at") or "")[:10]
    if not scraped:
        return None
    try:
        return (date.today() - date.fromisoformat(scraped)).days
    except ValueError:
        return None


def upcoming_events(within_days=None) -> list[dict]:
    """Events that have not already happened, soonest first."""
    today = date.today().isoformat()
    events = [e for e in _load().get("events", []) if (e.get("starts_on") or "")[:10] >= today]
    if within_days is not None:
        cutoff = (date.today() + timedelta(days=within_days)).isoformat()
        events = [e for e in events if e["starts_on"][:10] <= cutoff]
    return sorted(events, key=lambda e: e["starts_on"])


def is_stale() -> bool:
    """True when ACE should stop quoting this snapshot as current."""
    age = snapshot_age_days()
    if age is None or age > STALE_AFTER_DAYS:
        return True
    return not upcoming_events()


def _tokens(text: str) -> set[str]:
    return {
        w for w in re.findall(r"[a-z]+", (text or "").lower())
        if len(w) > 3 and w not in _STOPWORDS
    }


def mentions_events(question: str) -> bool:
    q = (question or "").lower()
    return any(t in q for t in TRIGGERS)


def _window_for(question: str) -> int:
    q = (question or "").lower()
    if "today" in q or "tonight" in q:
        return 1
    if "tomorrow" in q:
        return 2
    if "weekend" in q:
        return 7
    if "week" in q:
        return 7
    if "month" in q:
        return 31
    return 14


def find_events(question: str, interests=None, limit=MAX_EVENTS) -> list[dict]:
    """Upcoming events, preferring ones that match the question or the student."""
    events = upcoming_events(within_days=_window_for(question))
    if not events:
        # Nothing in the asked-for window — widen rather than answer with nothing.
        events = upcoming_events()
    if not events:
        return []

    wanted = _tokens(question)
    for phrase in interests or []:
        wanted |= _tokens(phrase)
    if not wanted:
        return events[:limit]

    def score(e):
        haystack = _tokens(f"{e['name']} {e.get('description','')} "
                           f"{' '.join(e.get('categories') or [])} {e.get('theme','')}")
        return len(wanted & haystack)

    ranked = sorted(events, key=lambda e: (-score(e), e["starts_on"]))
    # Keep chronological order among equally-relevant events.
    return ranked[:limit] if score(ranked[0]) else events[:limit]


# Engage returns UTC. Penn State runs on Eastern, so printing the raw stored
# hour told a student an event started at 11 PM when it starts at 7 PM — four
# hours late, every time, for every event.
CAMPUS_TZ = ZoneInfo("America/New_York")


def local_time(iso: str) -> str:
    """'2026-08-07T23:00:00+00:00' -> 'Fri 7 Aug, 7:00 PM'."""
    try:
        dt = datetime.fromisoformat(iso).astimezone(CAMPUS_TZ)
    except (TypeError, ValueError):
        return (iso or "")[:16].replace("T", " ")
    return dt.strftime("%a %-d %b, %-I:%M %p")


def format_event(e: dict) -> str:
    when = local_time(e["starts_on"])
    bits = [f"  - {e['name']} — {when}"]
    if e.get("location"):
        bits.append(f"at {e['location']}")
    if e.get("organization"):
        bits.append(f"({e['organization']})")
    line = " ".join(bits)
    extra = f"\n      {e['url']}"
    if e.get("map_url"):
        extra += f"  |  directions: {e['map_url']}"
    return line + extra


def build_events_snippet(question: str, interests=None) -> str:
    """Grounding for "what's happening". '' when the question isn't about events."""
    if not mentions_events(question):
        return ""
    if not _load():
        return ""

    if is_stale():
        age = snapshot_age_days()
        return (
            "\n\n=== CAMPUS EVENTS — SNAPSHOT OUT OF DATE ===\n"
            f"ACE's event list was last refreshed {age if age is not None else 'an unknown number of'} "
            "days ago and can no longer be trusted as current. Do NOT name or date any "
            f"event. Tell the student to check {EVENTS_PAGE} for what is on."
        )

    matches = find_events(question, interests)
    if not matches:
        return ""

    lines = ["\n\n=== UPCOMING PENN STATE EVENTS ==="]
    lines += [format_event(e) for e in matches]
    lines.append(
        f"\nTimes above are already Eastern (campus time) — repeat them as given "
        f"and do not convert or adjust them. These are real events from ACE's "
        f"directory, refreshed "
        f"{snapshot_age_days()} day(s) ago. Do NOT invent events, times, or "
        f"locations, and do not describe "
        f"this as the complete list — the full calendar is at {EVENTS_PAGE}."
    )
    return "\n".join(lines)
