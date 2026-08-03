"""Finding the student organisations a particular student would actually want.

The career bracket used to refuse to name clubs, because ACE had none to name.
clubs.json fixes the data problem; this decides which handful of ~1300 orgs are
worth putting in front of one student.

Matching is deliberately plain text — no embeddings. Interests arrive as short
phrases ("dancing", "machine learning") and the corpus is a name plus a
sentence, so a weighted keyword score is both good enough and inspectable, which
matters when the answer names real organisations to a real student.
"""

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

CLUBS_FILE = Path(__file__).parent.parent / "data" / "clubs.json"
MAX_MATCHES = 6

# Words that match half the corpus and tell us nothing about fit.
_STOPWORDS = {
    "club", "clubs", "org", "orgs", "organization", "organizations", "society",
    "association", "penn", "state", "university", "park", "student", "students",
    "at", "the", "of", "and", "for", "in", "a", "an", "to", "psu", "campus",
    "i", "am", "interested", "want", "like", "love", "join", "into", "my",
    # Question scaffolding. When the student's own words are the search (no
    # remembered interest yet), these leak in and do real damage: "major"
    # matched "Systems Neuroscience Major", and a club whose blurb happened to
    # contain "what" outranked actual dance teams.
    "what", "which", "should", "would", "could", "where", "when", "how", "who",
    "why", "can", "do", "does", "did", "any", "are", "is", "there", "some",
    "good", "best", "get", "find", "looking", "look", "me", "you", "recommend",
    "suggest", "about", "with", "that", "this", "have", "has", "major", "majors",
    "thing", "things", "stuff", "something", "anything", "one", "ones",
}

# A student says "dancing"; the org is called "Dance Company". Stemming the
# long way is overkill — trimming common endings catches the cases that matter.
_SUFFIXES = ("ing", "ers", "er", "es", "s")


def _stem(word: str) -> str:
    for suffix in _SUFFIXES:
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {_stem(w) for w in words if w not in _STOPWORDS and len(w) > 2}


@lru_cache(maxsize=1)
def load_clubs() -> list[dict]:
    """Parsed clubs.json, cached. Empty list when the dataset isn't built yet."""
    if not CLUBS_FILE.exists():
        logger.warning("clubs.json missing at %s — club answers will fall back", CLUBS_FILE)
        return []
    try:
        data = json.loads(CLUBS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.error("clubs.json unreadable: %s", exc)
        return []

    clubs = data.get("clubs", [])
    for club in clubs:
        club["_tokens"] = _tokens(
            f"{club.get('name','')} {club.get('summary','')} "
            f"{' '.join(club.get('categories') or [])}"
        )
        club["_name_tokens"] = _tokens(club.get("name", ""))
    logger.info("clubs.json loaded: %d organisations", len(clubs))
    return clubs


def score_club(club: dict, phrases: list[set]) -> float:
    """How well one organisation matches, scored per interest phrase.

    Scoring each phrase separately is what keeps "machine learning" off "Adult
    Learner Programs": flattening every interest into one token bag makes a club
    matching just `learn` look as good as one matching both words.
    """
    best = 0.0
    for wanted in phrases:
        if not wanted:
            continue
        # A hit in the NAME is worth far more than one buried in the blurb: an
        # org called "Dance Company" is about dancing; one whose description
        # happens to say "dance" may be a party-planning committee.
        name_hits = len(wanted & club.get("_name_tokens", set()))
        body_hits = len(wanted & club.get("_tokens", set()))
        if not (name_hits or body_hits):
            continue
        # How much of the phrase actually landed. Squared, so a half-matched
        # two-word interest ranks well below a fully-matched one.
        matched = len(wanted & (club.get("_tokens", set()) | club.get("_name_tokens", set())))
        coverage = (matched / len(wanted)) ** 2
        best = max(best, (name_hits * 3.0 + body_hits) * coverage)
    return best


# ponytail: weighted keyword match, not embeddings. Fine for short interest
# phrases against a name plus one sentence; if interests start arriving as
# sentences, this is the thing to replace.
_RELATIVE_FLOOR = 0.4


def search_clubs(interests, limit=MAX_MATCHES) -> list[dict]:
    """Organisations matching any of `interests`, best first.

    `interests` may be a list of phrases or one string. Returns [] when nothing
    scores — the caller must then say so rather than reaching for a near-miss.
    """
    if isinstance(interests, str):
        interests = [interests]
    phrases = [t for t in (_tokens(p) for p in interests or []) if t]
    if not phrases:
        return []

    scored = [(score_club(c, phrases), c) for c in load_clubs()]
    hits = sorted([(s, c) for s, c in scored if s > 0], key=lambda sc: -sc[0])
    if not hits:
        return []
    # Drop the long tail of weak partial matches: once one org clearly matches,
    # padding the list with near-misses makes the answer worse, not fuller.
    floor = hits[0][0] * _RELATIVE_FLOOR
    return [c for s, c in hits[:limit] if s >= floor]


def format_club_lines(clubs) -> list[str]:
    """One line per organisation, with whatever links it actually published."""
    lines = []
    for club in clubs:
        links = [f"profile {club['url']}"]
        if club.get("instagram"):
            links.append(f"Instagram {club['instagram']}")
        if club.get("website"):
            links.append(f"site {club['website']}")
        summary = (club.get("summary") or "")[:220]
        lines.append(
            f"  - {club['name']}"
            + (f" — {summary}" if summary else "")
            + f" [{'; '.join(links)}]"
        )
    return lines


def _major_terms(major: str) -> list[str]:
    """The searchable part of a program name: 'Computer Science, B.S. (Engineering)'
    → 'Computer Science'. Degree type and campus tell us nothing about clubs."""
    if not major:
        return []
    return [re.split(r"\s*,\s*", major)[0]]


def build_clubs_snippet(interests, question="", major="") -> str:
    """Grounding for a clubs question. '' when the dataset can't help.

    Three sources, in descending order of how much they say about this student:
    what ACE has learned they like, the words of the question ("are there dance
    clubs?"), and failing both, their major — "what clubs should I join as a CS
    major?" is all scaffolding words, but the major itself is a real signal.
    """
    if not load_clubs():
        return ""

    for basis, terms in (
        ("interests", interests),
        ("question", [question] if question else None),
        ("major", _major_terms(major)),
    ):
        matches = search_clubs(terms)
        if matches:
            break
    if not matches:
        return ""

    lines = [
        "\n\n=== MATCHING PENN STATE STUDENT ORGANISATIONS ===",
        f"(from ACE's organisation directory, matched on the student's {basis})",
    ]
    lines += format_club_lines(matches)
    lines.append(
        "\nName these organisations to the student and say what each one is, using "
        "the summary above. Include the links that are listed — the profile always, "
        "Instagram and website when present. Do NOT invent organisations, links, "
        "meeting times, or membership requirements beyond what is written here. "
        "These are the matches ACE found, not the complete list — tell the student "
        "the full directory is searchable at https://discover.psu.edu/organizations."
    )
    return "\n".join(lines)
