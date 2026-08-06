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

# Blocks the frontend can actually draw today. Telling the model to "let the
# block carry the structure" for a block with no renderer loses the information
# entirely — the student gets neither the list nor the picture. Add to this set
# only when a renderer ships.
RENDERED_BLOCKS = {"map", "cards", "checklist", "strip", "plan"}

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
    # "pre req" and "pre-req" are how students actually spell it; matching only
    # the closed-up form missed "map out the pre req map for these classes".
    r"\b(pre[\s-]?req\w*|pre[\s-]?requisite|eligible|can i take|am i able to take|"
    r"do i need .* before|unlocks?|unlocked|opens up|before i can take)\b", re.I
)

# When the block a question implies has no data but another block does, only a
# student who explicitly asked gets the fallback — otherwise ACE would answer a
# course question with whatever happened to be lying around.
_FALLBACK_ORDER = ("map", "plan", "checklist", "strip", "cards")
_PROCEDURE_QUESTION = re.compile(
    r"\b(how do i|what do i do|steps|process|petition|retroactive|withdraw)\b", re.I
)


# A strip is for a term at a glance. "When is the last day to drop?" wants one
# sentence with one date in it — drawing five deadlines around the answer buries
# the one they asked for.
_OVERVIEW_QUESTION = re.compile(
    r"\b(deadlines|dates|what'?s coming|coming up|what'?s due|this term|"
    r"this semester|calendar|key dates|important dates|overview)\b", re.I
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

    if not block:
        with_data = [b for b in _FALLBACK_ORDER if counts.get(b)]
        # One kind of structured material and only one — there is nothing to be
        # ambiguous about. "I failed a course and retook it" produced a
        # 4-step checklist that decide() could not reach, because the question
        # says neither "how do I" nor anything the intent's own block matches.
        if len(with_data) == 1:
            block = with_data[0]
        elif asked and with_data:
            # Several candidates: only honour the fallback when they asked, so a
            # course question is not answered with whatever was lying around.
            block = with_data[0]

    if not block:
        # Nothing structured to draw. If they asked anyway, say so rather than
        # inventing a diagram — that is how charts of nothing get made.
        return _out(0, None, False,
                    "no structured data for a visual" if asked else "prose answers this")

    if block == "strip" and not _OVERVIEW_QUESTION.search(q) and not asked:
        # A single date wants a sentence, not a term timeline. But refusing the
        # strip must not refuse the ANSWER: "I missed the late drop deadline,
        # what now?" routes to `deadline`, which claims the strip, which this
        # guard then declines — and the four-step petition checklist sitting
        # right there never got a look in. Decline the strip, then keep looking.
        alt = [b for b in _FALLBACK_ORDER if b != "strip" and counts.get(b)]
        if not alt:
            return _out(1, None, False,
                        "one date asked for — a sentence beats a term timeline")
        block = alt[0]

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


# Presentation lives HERE and nowhere else. The grounding snippets used to end
# with their own instructions — "name these places and give the directions link",
# "name these organisations and include the links" — written back when every
# answer was prose. When a block started rendering underneath, the model was
# holding two orders at once and obeyed the more specific one: "where can I eat
# on campus?" came back as six numbered places with links, and then the same six
# as cards. The snippets now state only what is TRUE and what may not be
# claimed; how the items reach the student is this function's decision alone.
_NAME_THEM = (
    " When the grounding above lists real places, organisations, events, "
    "offices or steps, name them and include the links given for each — the "
    "student cannot see the data you were handed."
)
# "Do not list the same items again" was already in here, and the model bulleted
# them anyway — a prohibition it can satisfy by changing the bullet character.
# What it needs is the shape it should produce instead, which is why the example
# is spelled out rather than described.
# The noun matters. Written as "every item", a checklist answer still came back
# with the four petition steps numbered out in full — the model did not read its
# steps as the "items" it was being told not to repeat.
_BLOCK_NOUN = {"map": "course", "cards": "item", "checklist": "step",
               "strip": "date", "plan": "course"}


def _block_has_them(block):
    noun = _BLOCK_NOUN.get(block, "item")
    return (
        f" Every {noun} is already in that block, with its detail and its links. "
        f"Do NOT reproduce the {noun}s in any form — no bullets, no numbering, no "
        f"bolded names, no per-{noun} links, and no sentence that runs through them "
        f"all in a row. Name at most TWO, and only where one genuinely stands out; "
        f"describe the rest by what they have in common — how many, where they "
        f"cluster, what the set means. Two or three sentences: the direct answer, "
        f"and the one thing the student needs that the block cannot say. Shape to "
        f"copy: \"There are six spots across the East, South and HUB districts — "
        f"they're below, with directions. Hours shift every term, so check the live "
        f"page before you walk over.\""
    )


def build_visual_directive(question, intent, counts=None, has_audit=False):
    """The prompt fragment telling the model how much visual to reach for."""
    d = decide(question, intent, counts, has_audit)
    if d["offer"] and d["block"]:
        return ("\n\nVISUAL POLICY: answer in prose. Do not produce a table or a "
                f"long list. End with exactly one short offer: \"{offer_line(d['block'])}\"")
    # These govern STRUCTURE, not length. Telling the model to be brief is how a
    # gen-ed answer loses the per-course explanation that made it useful — the
    # goal is to stop unwarranted scaffolding, not to withhold detail.
    if d["level"] == 0:
        return ("\n\nVISUAL POLICY: answer in prose. Do not build a table, an ASCII "
                "diagram, or a visual layout. A plain list is fine when the answer "
                "genuinely is a list of things — just don't dress it up. Give the "
                "detail the question deserves." + _NAME_THEM)
    if d["level"] == 1:
        return ("\n\nVISUAL POLICY: prose, with the key number or date stated once and "
                "clearly. No table and no diagram. Explain what it means for the "
                "student — the emphasis is on that one value, not on brevity."
                + _NAME_THEM)
    drawn = d["block"] in RENDERED_BLOCKS
    if d["level"] == 2:
        if drawn:
            return (f"\n\nVISUAL POLICY: a {d['block']} block is rendered beneath your answer."
                    + _block_has_them(d['block']))
        return (f"\n\nVISUAL POLICY: a compact {d['block']} is warranted, but nothing "
                "renders it — so the items must appear IN your answer. Lead with the "
                "direct answer, then list them, and say what each one means for this "
                "student.")
    if drawn:
        return (f"\n\nVISUAL POLICY: the student asked to see this, and a {d['block']} "
                "block is rendered beneath your answer. One framing sentence is enough."
                + _block_has_them(d['block']))
    return (f"\n\nVISUAL POLICY: the student asked to see this laid out, and nothing "
            f"renders it — so lay it out IN your answer as a full {d['block']}, with a "
            "framing sentence and whatever explanation the items need." + _NAME_THEM)
