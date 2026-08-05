"""Deciding when an answer deserves a visual — and, more often, when it doesn't.

Every ACE answer could be turned into a planner spread. Almost none should be.
A student asking "when is the drop deadline?" wants a sentence, and burying that
sentence in a timeline makes the product worse while looking like it got better.

So visuals are rationed by an escalation ladder. Most answers never leave level 0.

    0  prose only ................ the default, and the common case
    1  inline figure ............. one number or date given weight, still a sentence
    2  compact block ............. a bounded card, map or strip — 3-6 rows, contained
    3  full planner .............. the wide spread; only on a clear trigger or a request

Three ideas do the work:

* **Structure the prose can't carry.** A visual earns its place when the ANSWER has
  shape a sentence flattens: branching prerequisites (A or B, and C or D), several
  items compared across several terms, a sequence with dependencies. Not when it
  merely has data.
* **Enough content to fill it, and not too much.** One course is not a planner. Two
  dates are not a timeline. Twelve courses is not a card deck — that is an offer.
* **Some answers must stay plain.** Distress, visa, and money-decision questions get
  prose, always. A student in crisis does not need an infographic, and a chart
  lends unearned authority to a question ACE is deliberately refusing to answer.

When something would be useful but large or uncertain, ACE OFFERS instead of
rendering: "want me to map that out?" — one line, costs nothing, and the student
decides.
"""

import re

# ── The hard floor ──────────────────────────────────────────────────────────
# Intents that never get a visual, whatever the data says. Kept as an explicit
# list rather than a heuristic because these are the ones where being wrong is
# expensive rather than merely untidy.
NEVER_VISUAL_INTENTS = {
    "wellbeing",       # someone struggling does not need a chart
    "international",   # visa questions are referrals; a diagram implies advice
    "financial_aid",   # same — ACE refers, it does not counsel
    "contact",         # "email this office" is one sentence, forever
}

# The student explicitly wants to see something.
_ASKED_FOR_VISUAL = re.compile(
    # The pronoun is optional on purpose: "lay out my next two terms" is the
    # natural phrasing, and requiring "lay IT out" missed it entirely.
    r"\b(show me|map(?:\s+(?:it|this|that|them))?\s+out|map of|diagram|chart|graph|"
    r"visual(?:ise|ize|ly)?|lay(?:\s+(?:it|this|that|them|these))?\s+out|"
    r"plan(?:\s+(?:it|this|that))?\s+out|draw|picture|timeline|side by side|compare)\b", re.I
)

# The student explicitly wants brevity — outranks everything except the floor.
_ASKED_FOR_SHORT = re.compile(
    r"\b(just tell me|quickly|quick question|short answer|in one line|briefly|"
    r"tl;?dr|don'?t need details|simple answer)\b", re.I
)

# ── What each block needs before it may render ──────────────────────────────
# (block, minimum items, maximum items before it becomes an offer, the shape it
#  claims to show). Thresholds are the whole policy — below the minimum a
#  sentence is better, above the maximum the block stops being scannable.
BLOCK_RULES = {
    "map":       {"min": 2, "max": 12, "needs": "branching prerequisites"},
    "plan":      {"min": 3, "max": 18, "needs": "courses across terms"},
    "strip":     {"min": 3, "max": 8,  "needs": "dated events in one term"},
    "checklist": {"min": 3, "max": 10, "needs": "an ordered procedure"},
    "cards":     {"min": 2, "max": 8,  "needs": "comparable options"},
    "figure":    {"min": 1, "max": 2,  "needs": "a single number or date"},
}

# Which block an intent would use, if it qualifies at all.
INTENT_BLOCK = {
    "recommendation":   "plan",
    "courses":          "cards",
    "student_progress": "plan",
    "deadline":         "strip",
    "logistics":        "checklist",
    "gen_ed":           "cards",
    "career":           "cards",
    "general":          "cards",
}

# Questions about one course's eligibility are the strongest visual case there
# is — the AND/OR structure is genuinely unreadable as prose.
_PREREQ_QUESTION = re.compile(
    r"\b(prereq\w*|pre-?requisite|eligible|can i take|am i able to take|"
    r"do i need .* before|unlocks?|unlocked|opens up|before i can take)\b", re.I
)

# When the block a question implies has no data but another block does, only a
# student who explicitly asked gets the fallback — otherwise ACE would answer a
# course question with whatever happened to be lying around.
_FALLBACK_ORDER = ("map", "plan", "checklist", "strip", "cards")
_PROCEDURE_QUESTION = re.compile(
    r"\b(how do i|what do i do|steps|process|petition|retroactive|withdraw)\b", re.I
)


def decide(question, intent, counts=None, has_audit=False):
    """Choose the visual treatment for one answer.

    `counts` is what the services actually found — e.g. {"plan": 4, "strip": 2}.
    A block never renders on data that isn't there.

    Returns {level, block, offer, reason}. `offer` means: answer in prose, and
    add one line inviting the visual. `reason` is for logging and for the eval —
    every decision should be explainable after the fact.
    """
    counts = counts or {}
    q = question or ""

    if intent in NEVER_VISUAL_INTENTS:
        return _out(0, None, False, f"intent '{intent}' is prose-only by policy")

    if _ASKED_FOR_SHORT.search(q):
        return _out(0, None, False, "student asked for a short answer")

    asked = bool(_ASKED_FOR_VISUAL.search(q))

    # Which block is even on the table for this question?
    block = None
    if _PREREQ_QUESTION.search(q) and counts.get("map"):
        block = "map"
    elif _PROCEDURE_QUESTION.search(q) and counts.get("checklist"):
        block = "checklist"
    else:
        candidate = INTENT_BLOCK.get(intent)
        if candidate and counts.get(candidate):
            block = candidate

    if not block and asked:
        # They asked to see something and we do hold structured data — just not
        # the kind this intent usually reaches for. Use what exists.
        block = next((b for b in _FALLBACK_ORDER if counts.get(b)), None)

    if not block:
        # Nothing structured to draw. If they asked anyway, say so rather than
        # inventing a diagram — that is how charts of nothing get made.
        return _out(0, None, False,
                    "no structured data for a visual" if asked else "prose answers this")

    rule = BLOCK_RULES[block]
    n = counts.get(block, 0)

    if n < rule["min"]:
        return _out(1 if n else 0, None, False,
                    f"only {n} item(s) — below the {rule['min']} needed for a {block}")

    if n > rule["max"]:
        # Too big to be scannable. Offer it rather than dumping it.
        return _out(0, block, True,
                    f"{n} items exceeds {rule['max']} for a {block} — offer instead")

    if block == "figure":
        return _out(1, "figure", False, "single value worth weight, still prose")

    # A personal plan is only meaningful against a real record.
    if block == "plan" and not has_audit:
        return _out(0, "plan", True, "no audit uploaded — offer to plan once it is")

    if asked:
        return _out(3, block, False, f"student asked to see it; {n} items fit a {block}")

    # The default for qualifying structure: compact, contained, not full-bleed.
    return _out(2, block, False, f"{n} items with {rule['needs']} — compact {block}")


def _out(level, block, offer, reason):
    return {"level": level, "block": block if level or offer else None,
            "offer": offer, "reason": reason}


def offer_line(block):
    """The one-line invitation, when a visual is possible but not automatic."""
    return {
        "plan":      "Want me to lay this out as a term-by-term plan?",
        "map":       "Want me to map out what this unlocks?",
        "strip":     "Want these on a term timeline?",
        "checklist": "Want this as a checklist you can tick off?",
        "cards":     "Want me to break these out side by side?",
    }.get(block, "Want me to lay that out visually?")


def build_visual_directive(question, intent, counts=None, has_audit=False):
    """The prompt fragment telling the model how much visual to reach for."""
    d = decide(question, intent, counts, has_audit)
    if d["offer"] and d["block"]:
        return ("\n\nVISUAL POLICY: answer in prose. Do not produce a table or a "
                f"long list. End with exactly one short offer: \"{offer_line(d['block'])}\"")
    if d["level"] == 0:
        return ("\n\nVISUAL POLICY: prose only. No tables, no ASCII diagrams, no "
                "long bulleted breakdowns. Answer plainly and stop.")
    if d["level"] == 1:
        return ("\n\nVISUAL POLICY: prose, with the key number or date stated once "
                "and clearly. No table, no list of more than three items.")
    if d["level"] == 2:
        return (f"\n\nVISUAL POLICY: a compact {d['block']} is warranted — keep it to the "
                "items that answer the question, and keep the prose around it to two "
                "sentences. Do not restate the block in prose underneath it.")
    return (f"\n\nVISUAL POLICY: the student asked to see this. Produce the full "
            f"{d['block']}, and keep prose to a single framing sentence.")
