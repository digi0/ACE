"""What ACE remembers about a student between questions.

ACE knows a student's major and their audit. It has never known anything about
*them* — that they dance, that they want to end up in machine learning, that
they are trying to study abroad. Without that, every answer starts from zero and
"what clubs should I join?" can only ever be answered generically.

This module keeps a small profile, learned from the student's own words:

    {"interests": ["dancing", "hackathons"],
     "career_goals": ["machine learning"],
     "updated_at": "..."}

Three rules it follows:

1. Only the student's own statements. Never inferred from what ACE answered, and
   never from their audit — a course you were required to take is not an interest.
2. Extraction is gated. Most messages carry no personal signal, so a cheap regex
   decides whether the LLM call is worth making at all.
3. Nothing here is load-bearing. A failure to extract or store must never affect
   the answer the student is waiting on.
"""

import json
import logging
import re
from datetime import datetime, timezone

from backend.database import SessionLocal
from backend.models import User

logger = logging.getLogger(__name__)

MAX_INTERESTS = 12
MAX_GOALS = 6

# Cheap gate: only phrasings where a student is plausibly saying something about
# themselves. "What do I need to take" is not one; "I want to work in games" is.
# Cheaper to skip a real signal than to pay for an LLM call on every message.
_SIGNAL_CUES = re.compile(
    r"\b("
    r"i'?m interested in|i am interested in|i'?m into|interested in|"
    r"i like|i love|i enjoy|i'?m passionate|my passion|"
    r"i want to (?:be|become|work|go|get into|do)|i'?d like to (?:be|become|work)|"
    r"i hope to|my goal|my dream|i'?m hoping to|i plan to|"
    r"i play|i dance|i sing|i run|i volunteer|"
    r"career in|work in|job in|become an?|end up in|"
    r"i'?m a|i'?m an|my background"
    r")\b",
    re.I,
)

_EXTRACT_SYSTEM = (
    "You extract a student's personal interests and career direction from things "
    "they say to an academic advisor. Return JSON only: "
    '{"interests": [...], "career_goals": [...]}. '
    "Rules: only what the student states about THEMSELVES. An interest is a "
    "hobby, activity, or subject they are drawn to ('dancing', 'hackathons', "
    "'rock climbing'). A career goal is a field or role they want ('machine "
    "learning', 'medical school', 'game development'). Use short lowercase noun "
    "phrases, 1-3 words. Do NOT include their major, courses they must take, "
    "administrative topics, or anything they merely asked about. If they state "
    "nothing personal, return empty lists. Empty is the common, correct answer."
)


def _load(user) -> dict:
    try:
        return json.loads(user.profile_json) if user.profile_json else {}
    except (TypeError, ValueError):
        return {}


def _merge(existing: list, incoming: list, cap: int) -> list:
    """Append what's new, case-insensitively, newest last, capped."""
    out = list(existing or [])
    seen = {str(x).strip().lower() for x in out}
    for item in incoming or []:
        value = str(item).strip()
        if not value or len(value) > 60 or value.lower() in seen:
            continue
        seen.add(value.lower())
        out.append(value)
    return out[-cap:]


def extract_signals(text: str) -> dict:
    """Interests and goals stated in one message. {} when there is nothing."""
    if not text or not _SIGNAL_CUES.search(text):
        return {}
    from backend.services import llm

    try:
        raw = llm.chat(
            [{"role": "system", "content": _EXTRACT_SYSTEM},
             {"role": "user", "content": text[:1000]}],
            response_format={"type": "json_object"},
            feature="profile_extract",
        )
        data = json.loads(raw)
    except Exception as exc:  # noqa: BLE001 — never breaks the answer path
        logger.warning("extract_signals | failed: %s", exc)
        return {}

    interests = [i for i in data.get("interests", []) if isinstance(i, str)]
    goals = [g for g in data.get("career_goals", []) if isinstance(g, str)]
    return {"interests": interests, "career_goals": goals} if (interests or goals) else {}


def remember(user_id: str, text: str) -> dict | None:
    """Learn from one student message. Returns the updated profile, or None.

    Called after the answer has already streamed, so the extraction call is off
    the student's critical path.
    """
    if not user_id:
        return None
    signals = extract_signals(text)
    if not signals:
        return None

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if not user:
            return None
        profile = _load(user)
        profile["interests"] = _merge(
            profile.get("interests"), signals.get("interests"), MAX_INTERESTS
        )
        profile["career_goals"] = _merge(
            profile.get("career_goals"), signals.get("career_goals"), MAX_GOALS
        )
        profile["updated_at"] = datetime.now(timezone.utc).isoformat()
        user.profile_json = json.dumps(profile)
        db.commit()
        logger.info("remember | user=%r interests=%d goals=%d", user_id,
                    len(profile["interests"]), len(profile["career_goals"]))
        return profile
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("remember | failed: %s", exc, exc_info=True)
        return None
    finally:
        db.close()


def get_profile(user_id: str, db=None) -> dict:
    """The stored profile, or {}. Safe to call with no session."""
    if not user_id:
        return {}
    own = db is None
    db = db or SessionLocal()
    try:
        user = db.get(User, user_id)
        return _load(user) if user else {}
    except Exception:  # noqa: BLE001
        return {}
    finally:
        if own:
            db.close()


def set_profile(user_id: str, interests=None, career_goals=None, db=None) -> dict:
    """Replace what ACE thinks it knows. This is how a student corrects it."""
    own = db is None
    db = db or SessionLocal()
    try:
        user = db.get(User, user_id)
        if not user:
            return {}
        profile = _load(user)
        if interests is not None:
            profile["interests"] = _merge([], interests, MAX_INTERESTS)
        if career_goals is not None:
            profile["career_goals"] = _merge([], career_goals, MAX_GOALS)
        profile["updated_at"] = datetime.now(timezone.utc).isoformat()
        user.profile_json = json.dumps(profile)
        db.commit()
        return profile
    finally:
        if own:
            db.close()


def build_profile_snippet(user_id: str) -> str:
    """The prompt block. Empty string when ACE knows nothing yet."""
    profile = get_profile(user_id)
    interests = profile.get("interests") or []
    goals = profile.get("career_goals") or []
    if not interests and not goals:
        return ""

    lines = ["\n\n=== WHAT ACE KNOWS ABOUT THIS STUDENT ==="]
    if interests:
        lines.append("Interests they have mentioned: " + ", ".join(interests))
    if goals:
        lines.append("Career direction they have mentioned: " + ", ".join(goals))
    lines.append(
        "Use this to make the answer about them — which requirement to prioritise, "
        "which kind of activity or opportunity to point at. Do not recite it back "
        "as a list, do not assume anything beyond it, and never let it override "
        "what they actually asked."
    )
    return "\n".join(lines)
