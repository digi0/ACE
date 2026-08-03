"""Build clubs.json — Penn State student organisations, with their own links.

ACE could not answer "I'm interested in dancing, what should I join?" with
anything but "go search OrgCentral yourself". This is the dataset that fixes
that, in the same shape as programs.json/courses.json: scraped offline, committed,
read by a service at request time. Never fetched during a request.

OrgCentral redirects to discover.psu.edu, which runs Anthology/Campus Labs
Engage. Engage has a public JSON API, so this reads structured records rather
than parsing HTML:

  search : /api/discovery/search/organizations  → name, summary, categories
  detail : /api/discovery/organization/bykey/{key} → Instagram, website, LinkedIn

Deliberately NOT stored: the organisation's listed contact email. Engage returns
a named student's personal @psu.edu address, and that does not belong in a file
ACE quotes into answers. The public profile URL is stored instead — the contact
is on it, for whoever actually needs it.

    python -m backend.data.clubs_scraper              # full run, writes clubs.json
    python -m backend.data.clubs_scraper --limit 25   # quick sample
    python -m backend.data.clubs_scraper --no-details # skip the per-club fetch
"""

import argparse
import json
import logging
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

BASE = "https://discover.psu.edu"
SEARCH_URL = f"{BASE}/api/discovery/search/organizations"
DETAIL_URL = f"{BASE}/api/discovery/organization/bykey/{{key}}"
PROFILE_URL = f"{BASE}/organization/{{key}}"
OUT_FILE = Path(__file__).parent / "clubs.json"

PAGE_SIZE = 100
DETAIL_WORKERS = 4      # polite: this is someone else's server
RETRIES = 3

_HEADERS = {"User-Agent": "ACE-advising-bot/1.0 (Penn State student advising tool)"}
_TAG_RE = re.compile(r"<[^>]+>")


def _get(url, params=None):
    """GET with retries. Returns parsed JSON or None."""
    for attempt in range(RETRIES):
        try:
            r = requests.get(url, params=params, headers=_HEADERS, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            logger.warning("%s → HTTP %s (attempt %d)", url, r.status_code, attempt + 1)
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s → %s (attempt %d)", url, exc, attempt + 1)
        time.sleep(1 + attempt)
    return None


def clean_html(text: str) -> str:
    """Engage descriptions are HTML fragments; the prompt wants plain text."""
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>|</p>", " ", text, flags=re.I)
    text = _TAG_RE.sub("", text)
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&#39;", "'").replace("&quot;", '"')
                .replace("&rsquo;", "'").replace("&ldquo;", '"').replace("&rdquo;", '"'))
    return re.sub(r"\s+", " ", text).strip()


def fetch_page(skip: int, top: int = PAGE_SIZE) -> tuple[list, int]:
    """One page of organisations, plus the total count."""
    data = _get(SEARCH_URL, {"orderBy[0]": "UpperName asc", "top": top, "skip": skip})
    if not data:
        return [], 0
    return data.get("value", []), int(data.get("@odata.count") or 0)


def fetch_all_organizations(limit=None) -> list[dict]:
    orgs, skip, total = [], 0, None
    while True:
        page, count = fetch_page(skip)
        if total is None:
            total = count
            logger.info("Engage reports %d organisations", total)
        if not page:
            break
        orgs.extend(page)
        logger.info("fetched %d / %s", len(orgs), total)
        if limit and len(orgs) >= limit:
            return orgs[:limit]
        skip += PAGE_SIZE
        if total and skip >= total:
            break
        time.sleep(0.2)
    return orgs


def fetch_links(key: str) -> dict:
    """Instagram / website / LinkedIn for one organisation."""
    data = _get(DETAIL_URL.format(key=key))
    social = (data or {}).get("socialMedia") or {}

    def pick(name):
        value = (social.get(name) or "").strip()
        return value or None

    return {
        "instagram": pick("InstagramUrl"),
        "website": pick("ExternalWebsite"),
        "linkedin": pick("LinkedInUrl"),
        "facebook": pick("FacebookUrl"),
        "twitter": pick("TwitterUrl"),
        "youtube": pick("YoutubeUrl"),
    }


def normalize(org: dict) -> dict:
    key = org.get("WebsiteKey") or ""
    categories = [c for c in (org.get("CategoryNames") or []) if c]
    return {
        "name": org.get("Name") or "",
        "short_name": org.get("ShortName") or "",
        "key": key,
        "url": PROFILE_URL.format(key=key) if key else BASE,
        # Summary is the org's own one-liner; description is the long version.
        "summary": clean_html(org.get("Summary") or "")[:400],
        "description": clean_html(org.get("Description") or "")[:1200],
        "categories": categories,
        "status": org.get("Status") or "",
    }


def build(limit=None, with_details=True) -> dict:
    raw = fetch_all_organizations(limit=limit)
    # Only orgs a student can actually find and join.
    clubs = [
        normalize(o) for o in raw
        if (o.get("Status") or "").lower() == "active"
        and (o.get("Visibility") or "Public").lower() == "public"
        and o.get("WebsiteKey")
    ]
    logger.info("%d active public organisations of %d fetched", len(clubs), len(raw))

    if with_details and clubs:
        logger.info("fetching links for %d organisations...", len(clubs))
        with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as pool:
            for club, links in zip(clubs, pool.map(lambda c: fetch_links(c["key"]), clubs)):
                club.update({k: v for k, v in links.items() if v})

    with_insta = sum(1 for c in clubs if c.get("instagram"))
    logger.info("%d of %d have an Instagram link", with_insta, len(clubs))

    return {
        "_about": (
            "Penn State student organisations from discover.psu.edu (Anthology Engage). "
            "Rebuild with `python -m backend.data.clubs_scraper`. Contact emails are "
            "deliberately not stored — they are individual students' addresses; the "
            "profile URL carries them for anyone who needs one."
        ),
        "source": BASE,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "count": len(clubs),
        "clubs": clubs,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Scrape Penn State student organisations.")
    ap.add_argument("--limit", type=int, default=None, help="stop after N organisations")
    ap.add_argument("--no-details", action="store_true", help="skip the per-club link fetch")
    ap.add_argument("--out", default=str(OUT_FILE))
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    data = build(limit=args.limit, with_details=not args.no_details)
    if not data["clubs"]:
        print("No organisations fetched — refusing to overwrite clubs.json.")
        return 1

    Path(args.out).write_text(
        json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {data['count']} organisations to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
