"""Answering "where do I eat / study / do laundry / park" from real campus data.

The wedge answers degree questions. This answers the questions a student
actually has most days, which the playbook argues is what keeps ACE open on a
Tuesday rather than twice a term.

The load-bearing behaviour here is about HOURS. places.json deliberately stores
none, because dining and library hours change by term and by day. ACE is given
the live hours page and told to link it. A confidently wrong "open until 8" is
worse than "here's the hours page" — it sends someone across campus for nothing.
"""

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

PLACES_FILE = Path(__file__).parent.parent / "data" / "places.json"
MAX_PLACES = 6

# What a student's words say about which part of campus they mean.
CATEGORY_TRIGGERS = {
    "dining": [
        "eat", "eating", "food", "dining", "dinner", "lunch", "breakfast",
        "hungry", "meal plan", "meal swipe", "commons", "cafe", "coffee",
        "late night food", "halal", "vegan", "vegetarian", "gluten",
        "where to eat", "restaurant", "dining hall",
        # How a hungry student actually types it.
        "starving", "grab food", "get food", "something to eat", "grab a bite",
    ],
    "housing": [
        "housing", "dorm", "dorms", "residence hall", "res hall", "live on campus",
        "living on campus", "roommate", "room rate", "move in", "move out",
        "apartment", "laundry", "summer housing", "break housing",
    ],
    "library": [
        "library", "libraries", "pattee", "paterno", "borrow", "check out a book",
        "course reserves", "research help", "librarian",
    ],
    "study_space": [
        "study space", "study spot", "place to study", "quiet space", "study room",
        "group study", "somewhere to study", "reserve a room",
        "somewhere quiet", "quiet place", "cram", "pull an all", "study session",
        # Bare "study" too: "where should I study tonight?" is the natural
        # phrasing and matched none of the phrases above. Guarded below, because
        # "study abroad" is a career question, not a room booking.
        "study",
    ],
    "recreation": [
        "gym", "work out", "workout", "fitness", "rec hall", "intramural",
        "im building", "pool", "swim", "climbing wall", "recreation", "sports",
        "exercise", "basketball court",
    ],
    "health": [
        "health center", "student health", "uhs", "doctor", "clinic", "sick",
        "counseling", "caps", "mental health", "therapy", "pharmacy",
        "immunization", "vaccine",
    ],
    "transit": [
        "bus", "buses", "shuttle", "cata", "get around campus", "transit",
        "ride", "how do i get to",
    ],
    "parking": [
        "parking", "park my car", "parking permit", "parking ticket", "tow",
        "where do i park", "parking pass", "garage",
        # Getting ticketed or towed is how most students meet this office.
        "ticket on my", "parking fine", "ticketed", "towed", "boot on my car",
    ],
    "it_printing": [
        "print", "printing", "printer", "wifi", "wi-fi", "it help", "computer lab",
        "software", "laptop", "canvas help", "password reset",
    ],
}
# `mail` had triggers and no data behind it. A trigger that can never pay out is
# a promise the dataset does not keep — add it back with the source that fills it.


@lru_cache(maxsize=1)
def _load() -> dict:
    if not PLACES_FILE.exists():
        logger.warning("places.json missing at %s", PLACES_FILE)
        return {}
    try:
        return json.loads(PLACES_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.error("places.json unreadable: %s", exc)
        return {}


def load_places() -> list[dict]:
    return _load().get("places", [])


def hours_url_for(category: str) -> str:
    return (_load().get("hours_urls") or {}).get(category, "")


def detect_categories(question: str) -> list[str]:
    """Which parts of campus a question is about, strongest first."""
    q = (question or "").lower()
    scored = []
    for category, triggers in CATEGORY_TRIGGERS.items():
        if category == "study_space" and "study abroad" in q:
            continue  # that is a career question, not a room booking
        hits = [t for t in triggers if t in q]
        if hits:
            scored.append((len(hits) * 10 + max(len(t) for t in hits), category))
    return [c for _, c in sorted(scored, reverse=True)]


def _relevance(place: dict, q: str) -> int:
    """Extra credit for a place the question actually names or describes."""
    score = 0
    words = {w for w in re.findall(r"[a-z]+", place["name"].lower()) if len(w) > 3}
    score += 3 * len(words & set(re.findall(r"[a-z]+", q)))
    for tag in place.get("good_for", []):
        if tag.lower() in q:
            score += 2
    return score


def find_places(question: str, limit=MAX_PLACES) -> list[dict]:
    categories = detect_categories(question)
    if not categories:
        return []
    places = load_places()
    if not places:
        return []

    q = (question or "").lower()
    picked = []
    for category in categories:
        matches = sorted(
            [p for p in places if p["category"] == category],
            key=lambda p: -_relevance(p, q),
        )
        picked.extend(matches)
        if len(picked) >= limit:
            break
    return picked[:limit]


def build_places_snippet(question: str) -> str:
    """Grounding for a where-on-campus question. '' when none fits."""
    matches = find_places(question)
    if not matches:
        return ""

    lines = ["\n\n=== PENN STATE CAMPUS PLACES & SERVICES ==="]
    for p in matches:
        bits = [f"  - {p['name']}"]
        if p.get("where"):
            bits.append(f"({p['where']})")
        bits.append(f"— {p['what_it_is']}")
        lines.append(" ".join(bits))
        if p.get("notes"):
            lines.append(f"      note: {p['notes']}")
        if p.get("phone"):
            lines.append(f"      phone: {p['phone']}")
        lines.append(f"      info: {p['url']}  |  directions: {p['map_url']}")

    hours_pages = sorted({p["hours_url"] for p in matches if p.get("hours_url")})
    if hours_pages:
        lines.append("\nLive hours: " + "  ".join(hours_pages))

    lines.append(
        "\nName these places, say what each is good for, and give the directions "
        "link. ACE does NOT store opening hours — they change by term and by day. "
        "Never state a time a place opens or closes; link the live hours page "
        "above and let the student check. Do not invent buildings, phone numbers, "
        "prices, or services beyond what is written here."
    )
    return "\n".join(lines)
