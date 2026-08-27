"""F-1 provisions — mapping a student's options without advising them.

ACE used to answer every visa question with one sentence: "that's handled by
your international student adviser." True, and useless. The student already
knew to go to ISSA; what they did not know is that Reduced Course Load exists,
so they dropped the course first and found out afterwards that they had been out
of status since the day the drop went through.

So this does the thing an adviser's intake does: it maps the terrain. Here are
the provisions that might fit your situation, here is what each requires, here
is what breaks if you get it wrong, and here is the question to walk in with.

THE LINE, and it is not a fudge:

    ACE names options.        Only a DSO decides.

ACE may repeat a published rule with its citation. ACE may NOT tell a student
they qualify, that they should file something, or what their status is — that is
individualised immigration guidance, only a Designated School Official is
authorised to give it, and being wrong costs someone their status rather than a
late fee.

Every answer carries the risk half. A provision without its danger is how a
student reads "you can take 6 credits" and drops to 6 credits unauthorised.
"""

import json
import logging
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

VISA_FILE = Path(__file__).parent.parent / "data" / "visa.json"
MAX_RECORDS = 5

# Immigration rules move — fees, processing times, STEM rules. A confidently
# stated stale rule is worse here than in any other dataset ACE has, so the
# guard is tighter than the events one and refuses the NUMBERS rather than the
# whole answer: the provisions still exist, only the figures go untrustworthy.
STALE_AFTER_DAYS = 120

ISSA_URL = "https://global.psu.edu/"
ISSA_APPOINTMENT = ("https://psu.starfishsolutions.com/starfish-ops/instructor/"
                    "serviceCatalog.html#/search?q=penn%20state%20global%20-%20ISSA")

# What a student's situation lands on. Written in the words students use, not
# the words the regulations use — "I want to drop a class" is how the Reduced
# Course Load question actually arrives.
TOPIC_TRIGGERS = {
    "reduced_course_load": [
        "drop a class", "drop a course", "dropping a class", "part time",
        "part-time", "reduced course load", "rcl", "fewer credits",
        "below full time", "under 12 credits", "withdraw from a class",
        "too many classes", "struggling with my classes", "medical leave",
    ],
    "full_time_enrollment": [
        "full time", "full-time", "how many credits", "credit requirement",
        "minimum credits", "online classes count", "online credits",
    ],
    "on_campus_work": [
        "work on campus", "campus job", "on-campus employment", "hours can i work",
        "20 hours", "work study", "get a job", "student job", "paid position",
    ],
    "cpt": [
        "cpt", "curricular practical training", "internship", "co-op", "coop",
        "unpaid internship", "work off campus", "off-campus job", "summer internship",
    ],
    "opt": [
        "opt", "optional practical training", "work after graduation",
        "work after i graduate", "job after graduation", "stem extension",
        "cap gap", "cap-gap", "h1b", "h-1b", "60 day", "60-day",
    ],
    "travel": [
        "travel signature", "travel outside", "leave the country", "go home",
        "re-enter", "reenter", "visa stamp", "travel abroad", "visit home",
    ],
    "i20": [
        "i-20", "i20", "extend my program", "program end date", "extension",
        "graduating late", "need more time to finish",
    ],
    "status_violation": [
        "out of status", "terminated", "sevis terminated", "violated my status",
        "lost my status", "reinstatement", "unauthorized", "did i break",
        "in trouble with my visa", "stopped attending",
    ],
    "grace_period": [
        "grace period", "after i graduate", "after graduation", "60 days",
        "when do i have to leave", "finish my degree",
    ],
    "transfer": ["transfer my sevis", "transfer to another school", "change schools"],
    "program_change": ["change my major", "change majors", "switch my major",
                       "change academic level", "second bachelor"],
    "ssn": ["social security", "ssn", "social security number"],
    "documents": ["lost my i-20", "stolen passport", "lost passport",
                  "update my address", "change my address"],
    "insurance": ["health insurance", "insurance requirement", "waive insurance"],
}

# Questions ACE must not answer even with the dataset open. These ask for a
# determination about one person, which is exactly the DSO's job.
_ASKS_FOR_DETERMINATION = re.compile(
    r"\b(am i (eligible|allowed|able|okay|ok|fine|in trouble|out of status)|"
    r"do i qualify|will i (qualify|be able|get|lose)|can i legally|"
    r"is (it|this) (ok|okay|legal|allowed|fine) (for me|if i)|"
    r"should i (file|apply|drop|take|do)|what should i do about my (status|visa)|"
    r"is my (status|visa|record) (ok|okay|still valid|fine))\b", re.I
)


@lru_cache(maxsize=1)
def _load() -> dict:
    if not VISA_FILE.exists():
        logger.warning("visa.json missing at %s", VISA_FILE)
        return {}
    try:
        return json.loads(VISA_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.error("visa.json unreadable: %s", exc)
        return {}


def load_records() -> list[dict]:
    return _load().get("records", [])


def snapshot_age_days() -> int | None:
    scraped = (_load().get("scraped_at") or "")[:10]
    if not scraped:
        return None
    try:
        # max(0, ...): scraped_at is UTC and date.today() is local, so a
        # fresh scrape can read as -1 and reach the prompt as
        # "refreshed -1 day(s) ago".
        return max(0, (date.today() - date.fromisoformat(scraped)).days)
    except ValueError:
        return None


def is_stale() -> bool:
    age = snapshot_age_days()
    return age is None or age > STALE_AFTER_DAYS


def asks_for_determination(question: str) -> bool:
    """True when the student is asking ACE to rule on their own case."""
    return bool(_ASKS_FOR_DETERMINATION.search(question or ""))


def detect_topics(question: str) -> list[str]:
    """Which provisions a situation might touch, strongest first."""
    q = (question or "").lower()
    scored = []
    for topic, triggers in TOPIC_TRIGGERS.items():
        hits = [t for t in triggers if t in q]
        if hits:
            scored.append((len(hits) * 10 + max(len(t) for t in hits), topic))
    return [t for _, t in sorted(scored, reverse=True)]


def find_provisions(question: str, limit=MAX_RECORDS) -> list[dict]:
    topics = detect_topics(question)
    if not topics:
        return []
    records = load_records()
    picked, seen = [], set()
    for topic in topics:
        for r in [x for x in records if x.get("topic") == topic]:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            picked.append(r)
            if len(picked) >= limit:
                return picked
    return picked


def format_provision(r: dict) -> str:
    bits = [f"  --- {r['title']} ---",
            f"  What it is: {r['what_it_is']}"]
    if r.get("when_it_applies"):
        bits.append(f"  When it applies: {r['when_it_applies']}")
    if r.get("conditions"):
        bits.append("  Conditions: " + "; ".join(r["conditions"][:5]))
    if r.get("numbers"):
        bits.append("  Stated limits: " + "; ".join(r["numbers"][:4]))
    if r.get("risk_if_wrong"):
        bits.append(f"  RISK IF DONE WRONG: {r['risk_if_wrong']}")
    if r.get("side_effects"):
        bits.append("  Knock-on effects: " + "; ".join(r["side_effects"][:3]))
    if r.get("who_authorises"):
        bits.append(f"  Who approves it: {r['who_authorises']}")
    if r.get("how_to_start"):
        bits.append(f"  First step: {r['how_to_start']}")
    if r.get("ask_adviser"):
        bits.append(f"  Question to bring to ISSA: {r['ask_adviser']}")
    bits.append(f"  Source: {r['source_url']}")
    return "\n".join(bits)


def build_visa_snippet(question: str) -> str:
    """Grounding for an F-1 question. '' when the question isn't one."""
    matches = find_provisions(question)
    if not matches:
        return ""

    age = snapshot_age_days()
    lines = ["\n\n=== F-1 PROVISIONS THAT MAY FIT THIS SITUATION (options, NOT advice) ==="]
    lines += [format_provision(r) for r in matches]

    lines.append(
        "\nANSWERING RULES FOR THIS TOPIC — read them, they are not boilerplate:\n"
        "- Your job is to MAP OPTIONS, not to decide. Name the provisions above "
        "that could fit, say what each requires, and say what it costs to get "
        "wrong. The student almost certainly did not know these existed; that is "
        "the whole value of the answer.\n"
        "- Never tell the student they qualify, are eligible, are in status, or "
        "should file something. You do not know their visa type, program end "
        "date, prior history, or record. Only a DSO at ISSA can determine any of "
        "it, and being wrong here costs someone their status.\n"
        "- ALWAYS pair a provision with its risk. 'You can enrol in 6 credits' "
        "without 'dropping below full-time WITHOUT authorisation is a violation "
        "the day it happens' is the sentence that gets someone deported.\n"
        "- Quote the stated limits exactly as written above. Never estimate a "
        "credit count, a deadline, a duration or a fee, and never fill a gap "
        "from general knowledge of immigration law.\n"
        "- End by naming the questions to bring to ISSA (they are listed above) "
        f"and how to reach them: {ISSA_URL} — appointments at {ISSA_APPOINTMENT}\n"
        "- The office is ISSA (International Student and Scholar Advising), part "
        "of Penn State Global. Do not call it DISSA.\n"
        "- If the situation is unclear, ask ONE specific clarifying question "
        "before mapping — what their visa type is, what they are trying to do, or "
        "what their timeline is. Do not interrogate."
    )

    if is_stale():
        lines.append(
            f"\nSNAPSHOT IS {age if age is not None else 'AN UNKNOWN NUMBER OF'} DAYS OLD. "
            "Immigration figures change. Describe the provisions and what they are "
            "for, but do NOT state any specific number, deadline, fee or duration "
            "as current — tell the student to confirm every figure with ISSA."
        )
    elif age is not None:
        lines.append(f"\n(Provisions above were read from Penn State Global {age} day(s) ago.)")

    if asks_for_determination(question):
        lines.append(
            "\nTHIS STUDENT IS ASKING YOU TO RULE ON THEIR OWN CASE. Say plainly, "
            "early, and without hedging that you cannot determine their status or "
            "eligibility — only a DSO at ISSA can. Then map the options anyway, "
            "because knowing what to ask for is the useful part. Do not soften "
            "the refusal into an implied yes."
        )
    return "\n".join(lines)
