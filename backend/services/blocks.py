"""Turning what the services found into the payloads the frontend draws.

visual_policy decides WHETHER a block is warranted and which kind. This builds
the data for it. The two are deliberately separate: the policy can say "a plan
is warranted" long before a planner renderer exists, and this module can add a
payload without changing a single decision.

Every builder returns None when it has nothing real to show, so a block is never
drawn empty — the same rule the datasets follow.
"""

import logging
import re
from datetime import date, datetime

logger = logging.getLogger(__name__)


def _clip(text: str, limit: int) -> str:
    """Cut on a word, not through one. A hard slice ended a dining card on
    'accepted at every Campus Dining loca', which reads as a rendering bug."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.") + "…"


def _iso_days_away(iso: str) -> int | None:
    try:
        return (date.fromisoformat(iso[:10]) - date.today()).days
    except (TypeError, ValueError):
        return None


# ── cards ────────────────────────────────────────────────────────────────────

def clubs_cards(clubs):
    items = []
    for c in clubs:
        links = [{"label": "profile", "url": c["url"]}]
        if c.get("instagram"):
            links.append({"label": "instagram", "url": c["instagram"]})
        if c.get("website"):
            links.append({"label": "website", "url": c["website"]})
        items.append({"title": c["name"].replace(" at University Park", ""),
                      "body": _clip(c.get("summary"), 180), "links": links})
    return {"kind": "clubs", "items": items} if items else None


def places_cards(places):
    items = []
    for p in places:
        links = [{"label": "info", "url": p["url"]}]
        # A meal plan is not somewhere you can walk to. Its map_url is a Google
        # search for its own name, which lands nowhere — offer directions only
        # when the record names a place specific enough to stand in front of.
        where = (p.get("where") or "").strip()
        if p.get("map_url") and where and where.lower() not in {"campus", "university park"}:
            links.append({"label": "directions", "url": p["map_url"]})
        items.append({"title": p["name"], "meta": where,
                      "body": _clip(p.get("what_it_is"), 160), "links": links})
    hours = sorted({p["hours_url"] for p in places if p.get("hours_url")})
    return {"kind": "places", "items": items, "hours_url": hours[0] if hours else ""} if items else None


def events_cards(events, local_time):
    items = []
    for e in events:
        links = [{"label": "details", "url": e["url"]}]
        if e.get("map_url"):
            links.append({"label": "directions", "url": e["map_url"]})
        items.append({"title": e["name"], "meta": local_time(e["starts_on"]),
                      "body": (e.get("location") or "") + (
                          f" · {e['organization']}" if e.get("organization") else ""),
                      "links": links})
    return {"kind": "events", "items": items} if items else None


def course_cards(propose):
    """Slots from build_recommendation_context — one card per slot, not per option."""
    items = []
    for c in propose:
        alts = c.get("alternatives") or []
        blocked = c.get("unmet_prereqs") or []
        items.append({
            "title": c["code"], "subtitle": c.get("title") or "",
            "value": c.get("credits"), "unit": "cr",
            "meta": ("or " + ", ".join(alts)) if alts else "",
            "state": "blocked" if blocked else "ok",
            "note": ("needs " + ", ".join(blocked) + " first") if blocked else "",
        })
    return {"kind": "courses", "items": items} if items else None


# ── checklist ────────────────────────────────────────────────────────────────

def procedure_checklist(procedures):
    """The demo's Route block: ordered steps plus the facts rail beside them."""
    p = next((x for x in procedures if x.get("steps")), None)
    if not p:
        return None
    facts = []
    if p.get("timing"):
        facts.append({"k": "timing", "v": p["timing"][:120]})
    if p.get("who_to_contact"):
        facts.append({"k": "who handles it", "v": p["who_to_contact"][:120]})
    if p.get("forms"):
        facts.append({"k": "forms", "v": ", ".join(p["forms"])[:120]})
    if p.get("policy_refs"):
        facts.append({"k": "policy", "v": ", ".join(p["policy_refs"])})
    # what_it_is / when_to_use ride along for grounding_summary, not for the
    # renderer. Without them the model filled the gap it could feel — one run
    # invented "medical or personal circumstances" as the qualifying grounds.
    return {"title": p["title"], "steps": p["steps"][:8], "facts": facts,
            "source": p.get("source_url", ""),
            "what_it_is": p.get("what_it_is", ""), "when_to_use": p.get("when_to_use", "")}


# ── plan ─────────────────────────────────────────────────────────────────────

def term_plan(ctx, total_credits=None, completed_credits=None):
    """The planner spread: the outstanding slate as one term, with a credit total."""
    if not ctx or not ctx.get("propose"):
        return None
    courses, total = [], 0
    for c in ctx["propose"]:
        cr = c.get("credits")
        try:
            total += float(str(cr).split("-")[0])
        except (TypeError, ValueError):
            pass
        courses.append({"code": c["code"], "title": c.get("title") or "",
                        "credits": cr, "blocked": bool(c.get("unmet_prereqs")),
                        "alternatives": c.get("alternatives") or []})
    term = {"label": str(ctx.get("position") or "next term").replace("_", " ").title(),
            "courses": courses, "total": int(total) if total == int(total) else total}
    out = {"terms": [term], "personalised": bool(ctx.get("personalised"))}
    if total_credits:
        out["progress"] = {"done": completed_credits or 0, "total": total_credits}
    return out


# ── grounding, when the block is the one carrying the items ──────────────────

def grounding_summary(block: str, data: dict) -> str:
    """What the model is told INSTEAD of the itemised list, once a block renders.

    Telling it "a block is rendered, don't repeat the items" while also handing it
    the full list is asking it to ignore data sitting in front of it, and it
    complied about half the time — the same dining question came back as six
    bullets on one run and two clean sentences on the next. Prompt wording was not
    the lever. Withholding the list is: the model cannot transcribe what it was
    never given, so what reaches the student is the block, every time.

    What survives is what prose still has to carry — how many, where they cluster,
    the one shared link, and the office or timing a student has to act on.
    """
    if not data:
        return ""
    lines = []

    if block == "cards":
        items = data.get("items") or []
        if not items:
            return ""
        kind = {"places": "campus locations", "clubs": "student organisations",
                "events": "upcoming events", "courses": "courses"}.get(
                    data.get("kind"), "options")
        lines.append(f"{len(items)} {kind} are rendered in a block below your answer.")
        clusters = sorted({(i.get("meta") or "").strip() for i in items} - {""})
        if clusters:
            lines.append("They sit across: " + ", ".join(clusters[:6]) + ".")
        if data.get("hours_url"):
            lines.append(f"Shared live-hours page (link this): {data['hours_url']}")

    elif block == "checklist":
        lines.append(f"An ordered checklist for \"{data.get('title', '')}\" is "
                     f"rendered below your answer, with every step in it.")
        if data.get("what_it_is"):
            lines.append(f"What it is: {data['what_it_is']}")
        if data.get("when_to_use"):
            lines.append(f"When a student uses it: {data['when_to_use']}")
        # The office and the timing are the parts a student ACTS on, so those
        # stay in prose even though the block also shows them.
        for f in data.get("facts") or []:
            lines.append(f"{f['k']}: {f['v']}")
        if data.get("source"):
            lines.append(f"Source — ALWAYS include this link: {data['source']}")

    elif block == "strip":
        lines.append(f"{len(data.get('events') or [])} dated deadlines for "
                     f"{data.get('term', 'this term')} are rendered below.")

    elif block == "plan":
        n = sum(len(t.get("courses") or []) for t in data.get("terms") or [])
        total = sum(t.get("total") or 0 for t in data.get("terms") or [])
        lines.append(f"A term plan of {n} courses ({total} credits) is rendered below.")
        if not data.get("personalised"):
            lines.append("No audit is uploaded, so this is the standard slate for the "
                         "program rather than a personal plan — say so.")
        blocked = [c for t in data.get("terms") or []
                   for c in t.get("courses") or [] if c.get("blocked")]
        if blocked:
            lines.append(f"{len(blocked)} of them are blocked by unmet prerequisites — "
                         f"the block marks which.")

    elif block == "map":
        # The one block whose grounding is the ANSWER, not a list. A student
        # asking "can I take 465?" needs the verdict and the specific thing
        # standing in the way; they do not need every prerequisite recited,
        # which is what the map is for.
        target = data.get("target") or {}
        lines.append(f"A prerequisite map for {target.get('code','')} is rendered below, "
                     f"with every prerequisite and what the course opens.")
        if data.get("has_record"):
            if data.get("eligible"):
                lines.append("VERDICT: eligible now — every prerequisite is complete.")
            elif data.get("on_track"):
                lines.append("VERDICT: on track — every requirement is either done or "
                             "in progress this term, so it clears before next term.")
            else:
                lines.append("VERDICT: not yet eligible — at least one requirement is "
                             "untouched.")
        else:
            # Without a record, "still outstanding" is a claim about a student
            # whose transcript we have never seen — it came back as "No, you
            # cannot take CMPSC 465" for someone we know nothing about. The map
            # states the requirement; the prose must not personalise it.
            lines.append("No audit is uploaded, so ACE does not know what this "
                         "student has taken. Do NOT say they can or cannot take it, "
                         "and do NOT list what they still need. Say what the course "
                         "requires in general and point at the map.")
            return _wrap(lines)
        # With a record, only the courses actually in play get named: what they
        # are sitting in, and what is still untouched. Usually nought to two.
        doing, todo = [], []
        for group in data.get("groups") or []:
            if any(n.get("done") for n in group):
                continue
            for n in group:
                (doing if n.get("in_progress") else todo).append(n.get("code", ""))
        if doing:
            lines.append("In progress right now: " + ", ".join(doing))
        if todo and not doing:
            lines.append("Still outstanding: " + ", ".join(todo[:3]))

    return _wrap(lines)


def _wrap(lines: list[str]) -> str:
    if not lines:
        return ""
    return (
        "\n\n=== RENDERED BLOCK (the student sees these; you have NOT been given "
        "the individual entries) ===\n"
        + "\n".join(lines)
        + "\nWrite about the set, not the entries. Do not name, list, number or "
        "invent individual entries beyond what is written above — the block already "
        "shows every one. Do not state opening hours, prices, or dates that are "
        "not written above."
    )


# ── strip ────────────────────────────────────────────────────────────────────

_KEY_DEADLINE = re.compile(r"late drop|drop.*deadline|withdraw|final exam|"
                           r"first day|last day|registration|tuition", re.I)


def deadline_strip(calendar, limit=5):
    """The term strip: the next few dated deadlines, nearest first."""
    if not calendar:
        return None
    today = date.today().isoformat()
    rows = []
    for sem in calendar.get("semesters", []):
        for e in sem.get("events", []):
            iso = e.get("iso_date") or ""
            if iso >= today and _KEY_DEADLINE.search(e.get("event", "")):
                rows.append({"label": e["event"], "date": e.get("date", ""),
                             "iso": iso, "days": _iso_days_away(iso),
                             "term": sem.get("semester", "")})
    if not rows:
        return None
    rows.sort(key=lambda r: r["iso"])
    rows = rows[:limit]
    rows[0]["hot"] = True
    return {"term": rows[0]["term"], "events": rows}
