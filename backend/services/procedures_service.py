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
        "exception to the policy", "backdate", "appeal", "appealing",
        "make an exception", "ask for an exception", "special circumstances",
        "extenuating", "get out of this rule", "waive", "waiver", "override the rule",
        "is there any way", "who decides",
    ],
    # Leaving the whole term or the university. Kept distinct from late_drop by
    # scope: "get out of this semester" is here, "get out of one class" is not.
    "withdrawal": [
        "withdraw", "withdrawal", "withdrawing", "leave the university",
        "leaving the university", "drop out", "dropping out", "quit school",
        "quit college", "leave school", "leaving school", "leave penn state",
        "cancel my registration", "cancel registration", "stop attending",
        "stopped going", "stop going to class", "not going to class",
        "get out of this semester", "get out of the semester", "leave mid",
        "leave in the middle of the term", "leave in the middle of the semester",
        "don't want to be enrolled", "no longer enrolled", "unenroll from school",
    ],
    # ONE course, as opposed to the whole term above.
    "late_drop": [
        "late drop", "late-drop", "drop a class", "drop a course", "drop my class",
        "drop one class", "drop just one", "drop this class", "drop that class",
        "add a class", "add a course", "drop/add", "audit a course", "auditing",
        "get out of one class", "get out of a class", "get out of a course",
        "quit one class", "quit a class", "quit one course", "quit a course",
        "quit just one", "remove a class", "remove a course",
        "unenroll from a class", "take a class off", "off my schedule",
    ],
    "leave_of_absence": [
        "leave of absence", "take a semester off", "take a term off", "take a year off",
        "take time off", "time off from school", "take a break", "step away",
        "pause my degree", "pause school", "need time away", "need some time",
        "military leave", "deployed", "medical leave", "family emergency",
        "going through something", "can't be here this term",
    ],
    "re_enrollment": [
        "re-enroll", "reenroll", "re enrollment", "come back to penn state",
        "return to the university", "returning student", "academic renewal",
        "readmission", "was suspended", "come back after", "come back to school",
        "return to school", "start again", "finish my degree", "resume my degree",
        "was gone", "can i return", "get back in", "re-apply", "reapply",
        "left years ago", "want to finish", "finish what i started",
    ],
    "grades": [
        "grade forgiveness", "repeat a course", "retake a course", "deferred grade",
        "incomplete grade", "credit by exam", "challenge exam", "satisfactory",
        "unsatisfactory", "s/u grade", "pass fail", "academic warning",
        "academic suspension", "probation",
        # The names students actually use. Matching only the policy's own term
        # meant someone who knew to say "grade forgiveness" got the procedure and
        # someone describing what happened to them ("I retook it") got an
        # ungrounded guess — exactly backwards, since not knowing the vocabulary
        # is why they are asking.
        "retook", "retake", "retaking", "repeated", "repeating", "took it again",
        "take it again", "second attempt", "failed a course", "failed a class",
        "old grade", "previous grade", "first grade", "original grade",
        "grade removed", "remove the grade", "grade replaced", "grade replacement",
        "does the old grade", "still count", "replace my grade", "bad grade",
    ],
    "registration": [
        "late registration", "registration timetable", "when can i register",
        "when do i register", "enforced prerequisite", "prerequisite override",
        "multiple campus", "register at another campus", "can't sign up",
        "cannot sign up", "sign up for classes", "can't enroll", "cannot enroll",
        "why can't i enroll", "registration window", "won't let me add",
        "won't let me register", "system won't let me",
    ],
    "change_program": [
        "change my major", "change majors", "switch majors", "switch my major",
        "change of campus", "change campus", "switch campus", "transfer campus",
        "declare my major", "different major", "new major", "another major",
        "don't like my major", "switch what i'm studying", "study something else",
        "change what i study", "move to a different campus", "another campus",
        "change my degree",
    ],
    "graduation": [
        "apply for graduation", "intent to graduate", "graduating", "commencement",
        "diploma", "make sure i graduate", "actually graduate", "walk in may",
        "walk at graduation", "signed up to graduate", "am i graduating",
        "ready to graduate", "when i graduate",
    ],
    "transcripts": [
        "transcript", "official transcript", "order a transcript", "send my transcript",
        "grades sent", "send my grades", "copy of my record", "academic record",
        "academic history", "send to another school", "grad school wants",
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
        "\nDo NOT invent steps, forms, offices, fees, or deadlines beyond what is written "
        "above — this sends someone to file real paperwork, and a wrong step costs "
        "them a term. If the student's situation is not covered, say so and send "
        "them to their academic adviser or campus registrar."
    )
    return "\n".join(lines)
