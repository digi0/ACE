"""Build events.json — what is actually happening on campus.

Same Engage API as clubs_scraper, different endpoint. Cheap to add because the
client already exists.

UNLIKE every other ACE dataset, this one EXPIRES. Programs and procedures are
stable for a year; an events file is wrong within weeks. Two consequences,
both handled rather than ignored:

  1. Only future events are stored, with the window recorded in the file.
  2. events_service filters by today's date at read time and degrades to "check
     the live page" once the snapshot runs out — the same freshness guard
     _build_deadlines_snippet already applies to the academic calendar.

Re-run it weekly. If it has not been re-run, ACE says so instead of announcing
an event that happened last month.

    python -m backend.data.events_scraper
    python -m backend.data.events_scraper --days 60
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

BASE = "https://discover.psu.edu"
SEARCH_URL = f"{BASE}/api/discovery/event/search"
EVENT_URL = f"{BASE}/event/{{id}}"
EVENTS_PAGE = f"{BASE}/events"
OUT_FILE = Path(__file__).parent / "events.json"

PAGE_SIZE = 100
DEFAULT_DAYS = 90
_HEADERS = {"User-Agent": "ACE-advising-bot/1.0 (Penn State student advising tool)"}
_TAG_RE = re.compile(r"<[^>]+>")


def clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>|</p>", " ", text, flags=re.I)
    text = _TAG_RE.sub("", text)
    for entity, char in (("&nbsp;", " "), ("&amp;", "&"), ("&#39;", "'"),
                         ("&quot;", '"'), ("&rsquo;", "'"), ("&ldquo;", '"'),
                         ("&rdquo;", '"'), ("&mdash;", "—")):
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()


def fetch_page(skip: int, ends_after: str) -> tuple[list, int]:
    params = {
        "endsAfter": ends_after,
        "orderByField": "endsOn",
        "orderByDirection": "ascending",
        "status": "Approved",
        "take": PAGE_SIZE,
        "skip": skip,
    }
    try:
        r = requests.get(SEARCH_URL, params=params, headers=_HEADERS, timeout=30)
        if r.status_code != 200:
            logger.warning("events page skip=%d → HTTP %s", skip, r.status_code)
            return [], 0
        data = r.json()
        return data.get("value", []), int(data.get("@odata.count") or 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("events page skip=%d → %s", skip, exc)
        return [], 0


def normalize(e: dict) -> dict | None:
    name = (e.get("name") or "").strip()
    starts = e.get("startsOn") or ""
    if not name or not starts:
        return None

    lat, lon = e.get("latitude"), e.get("longitude")
    # Events carry real coordinates, so unlike places.json these are true pins
    # rather than a search guess.
    map_url = (
        f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
        if lat and lon else ""
    )
    return {
        "id": str(e.get("id") or ""),
        "name": name,
        "organization": (e.get("organizationName") or "").strip(),
        "description": clean_html(e.get("description") or "")[:500],
        "starts_on": starts,
        "ends_on": e.get("endsOn") or "",
        "location": (e.get("location") or "").strip(),
        "categories": [c for c in (e.get("categoryNames") or []) if c],
        "theme": e.get("theme") or "",
        "url": EVENT_URL.format(id=e.get("id")),
        "map_url": map_url,
    }


def build(days=DEFAULT_DAYS) -> dict:
    now = datetime.now(timezone.utc)
    ends_after = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    horizon = now + timedelta(days=days)

    events, skip, total = [], 0, None
    while True:
        page, count = fetch_page(skip, ends_after)
        if total is None:
            total = count
            logger.info("Engage reports %d upcoming events", total)
        if not page:
            break
        stop = False
        for raw in page:
            event = normalize(raw)
            if not event:
                continue
            # Ordered by end date, so once we pass the horizon we are done.
            if event["starts_on"][:10] > horizon.strftime("%Y-%m-%d"):
                stop = True
                break
            events.append(event)
        logger.info("collected %d event(s)", len(events))
        if stop:
            break
        skip += PAGE_SIZE
        if total and skip >= total:
            break
        time.sleep(0.2)

    return {
        "_about": (
            "Upcoming Penn State events from discover.psu.edu (Anthology Engage). "
            "THIS DATASET EXPIRES — re-run `python -m backend.data.events_scraper` "
            "weekly. events_service filters to future events at read time and falls "
            "back to the live page when the snapshot runs out."
        ),
        "source": EVENTS_PAGE,
        "scraped_at": now.isoformat(),
        "window_days": days,
        "count": len(events),
        "events": events,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Scrape upcoming Penn State events.")
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS)
    ap.add_argument("--out", default=str(OUT_FILE))
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    data = build(days=args.days)
    if not data["events"]:
        print("No events fetched — refusing to overwrite events.json.")
        return 1
    Path(args.out).write_text(
        json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {data['count']} events to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
