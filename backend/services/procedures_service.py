"""Matching a student's situation to the procedure that resolves it.

"I need to retroactively withdraw" used to route to `deadline` and come back
with a wall of dates — the calendar knows when the deadline was, which is
precisely the wrong answer for someone who has already missed it. procedures.json
holds what to actually do; this picks the right one.

Matched on explicit trigger phrases rather than free-text similarity: these
answers send a student to an office to file paperwork with a deadline attached,
so a near-miss is worse than no match. When nothing matches confidently, this
returns nothing and the other grounding handles the question.
"""

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

PROCEDURES_FILE = Path(__file__).parent.parent / "data" / "procedures.json"
MAX_PROCEDURES = 2  # two full procedures is already a long answer

# Phrases that pin a question to a topic. Order matters only in that a question
# can match several topics; all matches are scored and the best ones win.
TOPIC_TRIGGERS = {
    "petition": [
        "retroactive", "retroactively", "petition", "senate petition",
        "faculty senate", "after the deadline", "past the deadline",
        "missed the deadline", "too late to drop", "too late to withdraw",
        "exception to the policy", "backdate",
    ],
    "withdrawal": [
        "withdraw", "withdrawal", "withdrawing", "leave the university",
        "leaving the university", "drop out", "quit school", "cancel my registration",
        "cancel registration", "stop attending",
    ],
    "late_drop": [
        "late drop", "late-drop", "drop a class", "drop a course", "drop my class",
        "add a class", "add a course", "drop/add", "audit a course", "auditing",
    ],
    "leave_of_absence": [
        "leave of absence", "take a semester off", "take time off", "take a break",
        "pause my degree", "military leave", "deployed",
    ],
    "re_enrollment": [
        "re-enroll", "reenroll", "re enrollment", "come back to penn state",
        "return to the university", "returning student", "academic renewal",
        "readmission", "was suspended",
    ],
    "grades": [
        "grade forgiveness", "repeat a course", "retake a course", "deferred grade",
        "incomplete grade", "credit by exam", "challenge exam", "satisfactory",
        "unsatisfactory", "s/u grade", "pass fail", "academic warning",
        "academic suspension", "probation",
    ],
    "registration": [
        "late registration", "registration timetable", "when can i register",
        "enforced prerequisite", "prerequisite override", "multiple campus",
        "register at another campus",
    ],
    "change_program": [
        "change my major", "change majors", "switch majors", "change of campus",
        "change campus", "transfer campus", "declare my major",
    ],
    "graduation": [
        "apply for graduation", "intent to graduate", "graduating", "commencement",
        "diploma",
    ],
    "transcripts": [
        "transcript", "official transcript", "order a transcript", "send my transcript",
    ],
}


@lru_cache(maxsize=1)
def load_procedures() -> list[dict]:
    """Parsed procedures.json, cached. [] when the dataset isn't built."""
    if not PROCEDURES_FILE.exists():
        logger.warning("procedures.json missing at %s", PROCEDURES_FILE)
        return []
    try:
        data = json.loads(PROCEDURES_FILE.read_text(encoding="utf-8"))
        return data.get("procedures", [])
    except Exception as exc:  # noqa: BLE001
        logger.error("procedures.json unreadable: %s", exc)
        return []


# Missing a deadline is the single most load-bearing signal here: it turns a
# routine question into a petition. The trigger phrases can't catch it on their
# own because the words get separated — "missed the LATE DROP deadline".
_MISSED_DEADLINE = re.compile(
    r"\b(missed|too late|past|passed|after)\b.{0,30}\b(deadline|date|window|period)\b"
    r"|\b(deadline|window|period)\b.{0,20}\b(passed|closed|over|expired)\b",
    re.I,
)


def detect_topics(question: str) -> list[str]:
    """Topics a question plausibly concerns, strongest first."""
    q = (question or "").lower()
    scored = []
    if _MISSED_DEADLINE.search(q):
        # Ranked high deliberately: the calendar can tell them when the deadline
        # was, which is useless once it is behind them.
        scored.append((999, "petition"))
    for topic, triggers in TOPIC_TRIGGERS.items():
        hits = sum(1 for t in triggers if t in q)
        if hits:
            # Longer trigger phrases are more specific, so weight by the longest
            # one that matched: "retroactive late drop" should beat bare "drop".
            longest = max((len(t) for t in triggers if t in q), default=0)
            scored.append((hits * 10 + longest, topic))
    return [t for _, t in sorted(scored, reverse=True)]


def find_procedures(question: str, limit=MAX_PROCEDURES) -> list[dict]:
    """The procedures worth putting in front of this question."""
    topics = detect_topics(question)
    if not topics:
        return []
    procedures = load_procedures()
    if not procedures:
        return []

    q = (question or "").lower()
    picked, seen = [], set()
    for topic in topics:
        matches = [p for p in procedures if p.get("topic") == topic]
        # Within a topic, prefer the record whose own title the student echoed.
        matches.sort(
            key=lambda p: -sum(
                1 for w in re.findall(r"[a-z]+", p.get("title", "").lower())
                if len(w) > 4 and w in q
            )
        )
        for p in matches:
            if p["id"] in seen:
                continue
            seen.add(p["id"])
            picked.append(p)
            if len(picked) >= limit:
                return picked
    return picked


def format_procedure(p: dict) -> str:
    lines = [f"\n--- {p['title']} ---"]
    if p.get("what_it_is"):
        lines.append(p["what_it_is"])
    if p.get("when_to_use"):
        lines.append(f"When it applies: {p['when_to_use']}")
    if p.get("steps"):
        lines.append("Steps:")
        lines += [f"  {i}. {s}" for i, s in enumerate(p["steps"], 1)]
    if p.get("forms"):
        lines.append("Forms/documents: " + ", ".join(p["forms"]))
    if p.get("timing"):
        lines.append(f"Timing: {p['timing']}")
    if p.get("who_to_contact"):
        lines.append(f"Who handles it: {p['who_to_contact']}")
    if p.get("consequences"):
        lines.append(f"Consequences: {p['consequences']}")
    if p.get("policy_refs"):
        lines.append("Penn State policy: " + ", ".join(p["policy_refs"]))
    lines.append(f"Source: {p['source_url']}")
    return "\n".join(lines)


def build_procedures_snippet(question: str) -> str:
    """Grounding for a 'how do I actually do this' question. '' when none fits."""
    matches = find_procedures(question)
    if not matches:
        return ""

    lines = ["\n\n=== PENN STATE PROCEDURE (what the student actually does) ==="]
    lines += [format_procedure(p) for p in matches]
    lines.append(
        "\nWalk the student through these steps in order, name the form and the "
        "office, and state the timing rule if one is given. Link the source. Do NOT "
        "invent steps, forms, offices, fees, or deadlines beyond what is written "
        "above — this sends someone to file real paperwork, and a wrong step costs "
        "them a term. If the student's situation is not covered, say so and send "
        "them to their academic adviser or campus registrar."
    )
    return "\n".join(lines)
