"""Money questions ACE can answer, and the hard line it must not cross.

Two kinds of money question look alike and are not:

  "Who do I email about this charge?"      → navigation. ACE should answer it.
  "Should I take out this loan?"           → advice. ACE must not.

ACE already refused the second, correctly — aid eligibility and borrowing are
high-liability and belong to the Office of Student Aid. But it was refusing the
first too, and that one is the entire product. money.json covers the first; the
snippet below re-states the boundary so widening the data does not quietly
widen the advice.

The boundary is enforced in the prompt rather than by withholding data, because
the same page that says how refunds are issued also mentions aid disbursement —
the split is in what ACE DOES with it, not in what it can see.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

MONEY_FILE = Path(__file__).parent.parent / "data" / "money.json"
MAX_RECORDS = 3

STUDENT_AID_URL = "https://studentaid.psu.edu/"

# Navigational money questions — the ones this dataset answers.
TOPIC_TRIGGERS = {
    "contacts": [
        "who do i email", "who do i contact", "who should i call", "who handles",
        "bursar", "who do i talk to about my bill", "billing office",
    ],
    "refunds": [
        "refund", "refunded", "credit balance", "erefund", "money back",
        "overpaid", "direct deposit", "money i'm owed", "money im owed",
        "owed money", "owe me money", "get my money",
    ],
    "late_fees": [
        "late fee", "late payment", "past due", "delinquent", "financial hold",
        "didn't pay", "did not pay", "missed a payment", "balance due",
        "can't pay", "cannot pay", "can't afford the", "on hold", "account is on hold",
    ],
    "payments": [
        "pay my bill", "pay tuition", "make a payment", "payment plan",
        "credit card", "pay by check", "529", "how do i pay",
        "parents pay", "parents want to pay", "someone else pay", "pay for me",
        "authorized user", "third party pay",
    ],
    "billing": [
        "my bill", "tuition bill", "student account", "what is this charge",
        "what's this charge", "charge on my account", "invoice", "statement",
        "tuition due", "when is tuition due",
        "weird charge", "unexpected charge", "charge i don't", "don't recognise",
        "don't recognize", "being charged", "what am i paying for",
    ],
    "forms": ["bursar form", "student account form"],
    "third_party": ["third party billing", "employer pays", "sponsor", "sponsored billing"],
    "new_students": ["first tuition bill", "new student billing", "international student billing"],
}

# Questions that are ADVICE, not navigation. Detected so the snippet can name
# the boundary explicitly rather than hoping the model infers it.
_ADVICE_MARKERS = [
    "should i take", "should i borrow", "how much should i", "is it worth",
    "can i afford", "which loan", "best loan", "how much aid will i",
    "will i qualify", "am i eligible", "how much will i get", "do i qualify",
]


@lru_cache(maxsize=1)
def load_money() -> list[dict]:
    if not MONEY_FILE.exists():
        logger.warning("money.json missing at %s", MONEY_FILE)
        return []
    try:
        return json.loads(MONEY_FILE.read_text(encoding="utf-8")).get("money", [])
    except Exception as exc:  # noqa: BLE001
        logger.error("money.json unreadable: %s", exc)
        return []


def detect_topics(question: str) -> list[str]:
    q = (question or "").lower()
    scored = []
    for topic, triggers in TOPIC_TRIGGERS.items():
        hits = [t for t in triggers if t in q]
        if hits:
            scored.append((len(hits) * 10 + max(len(t) for t in hits), topic))
    return [t for _, t in sorted(scored, reverse=True)]


# The advice markers alone are not enough: "should i take" also matches "should I
# take CMPSC 121?", and a money disclaimer on a course question is noise. Advice
# only counts when the question is actually about money.
_MONEY_WORDS = [
    "loan", "loans", "borrow", "aid", "fafsa", "scholarship", "grant",
    "tuition", "afford", "pay", "paying", "cost", "money", "bill", "debt",
    "work study", "work-study", "refund", "charge",
]


def asks_for_advice(question: str) -> bool:
    """True when the student is asking ACE to make a money decision for them."""
    q = (question or "").lower()
    return (any(m in q for m in _ADVICE_MARKERS)
            and any(w in q for w in _MONEY_WORDS))


def find_money(question: str, limit=MAX_RECORDS) -> list[dict]:
    topics = detect_topics(question)
    if not topics:
        return []
    records = load_money()
    if not records:
        return []

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


def format_record(r: dict) -> str:
    lines = [f"\n--- {r['title']} ---"]
    if r.get("what_it_is"):
        lines.append(r["what_it_is"])
    if r.get("steps"):
        lines.append("Steps:")
        lines += [f"  {i}. {s}" for i, s in enumerate(r["steps"], 1)]
    if r.get("amounts"):
        lines.append("Stated amounts: " + "; ".join(r["amounts"]))
    if r.get("timing"):
        lines.append(f"Timing: {r['timing']}")
    if r.get("who_to_contact"):
        lines.append(f"Who to contact: {r['who_to_contact']}")
    if r.get("notes"):
        lines.append(f"Note: {r['notes']}")
    lines.append(f"Source: {r['source_url']}")
    return "\n".join(lines)


def build_money_snippet(question: str) -> str:
    """Grounding for a student-account question. '' when none applies."""
    matches = find_money(question)
    if not matches:
        # A pure advice question ("should I take out a loan?") matches no
        # navigational topic, so without this it would get no guardrail at all —
        # the one case where saying nothing is the most expensive answer.
        if asks_for_advice(question):
            return (
                "\n\n=== MONEY DECISION — OUT OF SCOPE ===\n"
                "This student is asking ACE to make a financial decision for them. "
                "ACE cannot see their aid package, balance, or eligibility, and does "
                "not advise on borrowing. Say so plainly, explain what the Office of "
                f"Student Aid can do, and point them there ({STUDENT_AID_URL}). Do "
                "not hedge into an opinion or estimate any amount."
            )
        return ""

    lines = ["\n\n=== PENN STATE STUDENT ACCOUNT (navigation, not advice) ==="]
    lines += [format_record(r) for r in matches]
    lines.append(
        "\nANSWERING RULES FOR THIS TOPIC:\n"
        "- Explain the process and name the office, with the phone number or form "
        "above. Quote stated fees exactly; never estimate one.\n"
        "- You do NOT have access to this student's account, balance, or aid "
        "package. Never state, guess, or calculate what they personally owe, are "
        "owed, or will receive.\n"
        "- When the question is about THEIR account specifically ('why haven't I "
        "received my refund', 'what is this charge'), say plainly and early that you "
        "cannot see their account, then explain how the process works and who can "
        "look it up. Leaving that implied reads as if you had checked.\n"
        "- Financial-aid ADVICE stays out of scope: eligibility, award amounts, "
        "whether to borrow, which loan to take. Explaining who to ask and how the "
        f"process works is fine; deciding for them is not. Send those to the Office "
        f"of Student Aid ({STUDENT_AID_URL}).\n"
        "- Do not invent fees, deadlines, offices, or email addresses."
    )
    if asks_for_advice(question):
        lines.append(
            "\nThis student is asking ACE to make a financial decision for them. "
            "Answer the navigational part if there is one, then say plainly that the "
            "decision needs the Office of Student Aid, who can see their actual "
            "package. Do not hedge into an opinion."
        )
    return "\n".join(lines)
