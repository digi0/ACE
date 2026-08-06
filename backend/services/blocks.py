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
                      "body": (c.get("summary") or "")[:180], "links": links})
    return {"kind": "clubs", "items": items} if items else None


def places_cards(places):
    items = []
    for p in places:
        links = [{"label": "info", "url": p["url"]}]
        if p.get("map_url"):
            links.append({"label": "directions", "url": p["map_url"]})
        items.append({"title": p["name"], "meta": p.get("where") or "",
                      "body": (p.get("what_it_is") or "")[:160], "links": links})
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
    return {"title": p["title"], "steps": p["steps"][:8], "facts": facts,
            "source": p.get("source_url", "")}


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
