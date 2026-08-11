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
        # Taken from what the eight health records themselves say they do —
        # "Fill prescriptions", "X-ray and imaging services", "lab work",
        # "University Ambulance Service" — because a student asks for the
        # SERVICE, not the department. "where can I get a prescription" matched
        # nothing at all while the Pharmacy record said it in as many words.
        "prescription", "prescriptions", "refill", "medication",
        "x-ray", "xray", "imaging", "radiology", "scan",
        "lab work", "blood test", "blood work", "bloodwork",
        "ambulance", "medical emergency", "urgent care",
        "physical therapy", "rehab", "injury", "injured", "illness",
        "breastfeeding", "lactation", "nurse", "checkup", "check-up",
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


# Signals that a question is about the DEGREE, not the campus. Lives here rather
# than in chat_service because places_service is the lower of the two and both
# need it — chat_service imports this one, so a second copy would drift.
ACADEMIC_CONTEXT = re.compile(
    r"\b(course|courses|class|classes|credit|credits|requirement|requirements|"
    r"prereq\w*|semester|term|major|minor|gen ?ed|elective|electives|degree|"
    r"transcript|gpa|graduate|graduation|advisor|adviser|audit|syllabus|exam|"
    r"[a-z]{2,6}\s?\d{3}[a-z]?)\b", re.I
)

# Multi-word triggers are safe as substrings — "where do i park" cannot hide
# inside another word. Single words cannot: "tow" lives in "toward", and "eat"
# lives in create, theater, repeated, great, heat and reseat, which is six of
# fourteen probe questions hijacked by one three-letter trigger. This is the
# same failure the intent router was fixed for; the fix never reached here.
_TRIGGER_RE: dict[str, re.Pattern] = {}


def _matches(trigger: str, q: str) -> bool:
    if " " in trigger or "-" in trigger:
        return trigger in q
    rx = _TRIGGER_RE.get(trigger)
    if rx is None:
        rx = _TRIGGER_RE[trigger] = re.compile(rf"\b{re.escape(trigger)}\b")
    return bool(rx.search(q))


def detect_categories(question: str) -> list[str]:
    """Which parts of campus a question is about, strongest first."""
    q = (question or "").lower()
    scored = []
    academic = bool(ACADEMIC_CONTEXT.search(q))
    for category, triggers in CATEGORY_TRIGGERS.items():
        if category == "study_space" and ("study abroad" in q or "study plan" in q):
            continue  # a term plan and a term abroad are not room bookings
        hits = [t for t in triggers if _matches(t, q)]
        if not hits:
            continue
        # A single short word is the weakest evidence there is, and next to an
        # academic question it is almost always coincidence: "I am SICK of my
        # major", "who teaches the GYM class requirement", "does the BUS
        # schedule affect my class times". A real place question either says so
        # in a phrase ("where do i eat") or names the place outright.
        if academic and all(len(t) <= 5 and " " not in t for t in hits):
            continue
        scored.append((len(hits) * 10 + max(len(t) for t in hits), category))
    return [c for _, c in sorted(scored, reverse=True)]


# Words that appear in half the directory and in nearly every question, so
# matching on them is noise dressed as a signal. "where can I eat on campus?"
# ranked Campus Meal Plan first — above every actual dining hall — on the
# strength of the word "campus" alone.
_GENERIC_NAME_WORDS = {
    "campus", "penn", "state", "university", "park", "student", "students",
    "center", "centre", "building", "hall", "services", "service",
}

# Words that carry no topic and appear in every other question — and, crucially,
# in every other DESCRIPTION. "I hurt my knee and need rehab" scored CAPS above
# Physical Therapy because CAPS has the longer paragraph and so contained "and"
# and "need" more often. Grammar was outvoting the one word that meant something.
_WEAK_WORDS = {
    "where", "what", "when", "which", "there", "here", "need", "needs", "want",
    "have", "does", "should", "could", "would", "will", "with", "from", "about",
    "some", "this", "that", "these", "those", "your", "yours", "mine", "help",
    "find", "look", "know", "make", "take", "give", "tell", "please", "thanks",
    "just", "like", "much", "many", "more", "most", "also", "into", "near",
    "around", "over", "and", "the", "for", "are", "but", "not", "you", "can",
    "was", "were", "its", "their", "them", "they", "through", "including",
    "available", "offers", "offering", "provide", "provides", "providing",
    "access", "various", "every", "well", "your",
}


# Hyphens are kept: splitting on them turns "x-ray" into "x" and "ray", and a
# three-letter fragment is below every length floor here, so the Radiology record
# — which says "X-ray and imaging services" — was unreachable by the word for it.
_WORD = re.compile(r"[a-z][a-z\-]{2,}")


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall((text or "").lower())
            if w not in _GENERIC_NAME_WORDS and w not in _WEAK_WORDS}


def _overlap(asked: set[str], described: set[str]) -> int:
    """How many asked-for words the text covers, allowing for word forms.

    Exact matching alone left "prescription" not matching "Fill prescriptions"
    and "rehab" not matching "rehabilitation" — so the record that literally
    describes the service lost to the category's front door. Prefix matching from
    five characters is enough for the endings that matter (-s, -es, -ing, -ation)
    without pulling "car" onto "carpark".
    """
    hits = 0
    for a in asked:
        if a in described:
            hits += 1
        elif len(a) >= 5 and any(d.startswith(a) or a.startswith(d)
                                 for d in described if len(d) >= 5):
            hits += 1
    return hits


def _relevance(place: dict, q: str) -> int:
    """Extra credit for a place the question actually names or describes."""
    asked = _words(q)
    score = 3 * _overlap(asked, _words(place["name"]))
    # good_for used to be matched by asking whether the whole tag appeared in the
    # question, so a student saying "rehab" never reached the record tagged
    # "rehabilitation" and lost to whichever record the front door favoured.
    score += 2 * _overlap(asked, _words(" ".join(place.get("good_for") or [])))
    # What a place DOES, not just what it is called. A student says "I need to
    # see a doctor"; no record is named "doctor", so on name alone every health
    # record scored zero and the answer led with whatever sat first in the file.
    score += _overlap(asked, _words(place.get("what_it_is")))
    return score


# A question can name a category and nothing inside it — "I need to see a doctor"
# matches no record by name or description, so every health record scored zero and
# whatever sat first in the file won. It was Lactation Rooms. The dataset now
# marks a front door per category where one genuinely exists; this breaks the tie.
def _rank(place: dict, q: str) -> tuple:
    return (-_relevance(place, q), 0 if place.get("primary") else 1)


def _described_by(question: str, places: list[dict]) -> list[str]:
    """Categories reachable through the records' OWN words, not the trigger list.

    "where can I get a prescription" matched nothing, while the Pharmacy record
    says "Fill prescriptions" in as many words. Hand-written triggers will always
    trail the data, so when they come up empty the descriptions are searched
    directly. Two distinct content words must land on the same record — one is
    how "what math courses do I need" turns into a campus map.
    """
    asked = {w for w in re.findall(r"[a-z]{4,}", (question or "").lower())
             if w not in _GENERIC_NAME_WORDS and w not in _WEAK_WORDS}
    if len(asked) < 2:
        return []
    best = {}
    for p in places:
        text = f"{p['name']} {p.get('what_it_is','')} {' '.join(p.get('good_for') or [])}".lower()
        hits = len(asked & set(re.findall(r"[a-z]{4,}", text)))
        if hits >= 2:
            best[p["category"]] = max(best.get(p["category"], 0), hits)
    return [c for c, _ in sorted(best.items(), key=lambda kv: -kv[1])]


def find_places(question: str, limit=MAX_PLACES) -> list[dict]:
    places = load_places()
    if not places:
        return []
    categories = detect_categories(question) or _described_by(question, places)
    if not categories:
        return []

    q = (question or "").lower()
    picked = []
    for category in categories:
        matches = sorted([p for p in places if p["category"] == category],
                         key=lambda p: _rank(p, q))
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
        "\nACE does NOT store opening hours — they change by term and by day. "
        "Never state a time a place opens or closes; link the live hours page "
        "above and let the student check. Do not invent buildings, phone numbers, "
        "prices, or services beyond what is written here."
    )
    return "\n".join(lines)
