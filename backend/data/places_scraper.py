"""Build places.json — the campus itself: dining, housing, libraries, rec, health,
transit, parking, printing.

This is the playbook's "Places & services" surface — "dining hours, library
floors, the gym, health and counselling, IT help, printing, parking appeals,
transit, mail and packages". ACE knew Penn State's degree requirements in
enormous detail and could not tell a student where to eat.

ONE RULE SHAPES THIS DATASET: hours are not stored as values.

Dining and library hours change by term, by day, and by building. A committed
JSON file cannot track that, and a confidently wrong "open until 8pm" sends a
hungry student across campus for nothing. So each place carries the URL of its
LIVE hours page, and the service tells ACE to link it rather than state a time.
The stable facts — what a place is, where it is, what it's for — are stored.

Map links are CONSTRUCTED Google Maps search URLs (place name + campus), not
verified pins. They are labelled as searches, because that is what they are.

    python -m backend.data.places_scraper
    python -m backend.data.places_scraper --limit 3
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

OUT_FILE = Path(__file__).parent / "places.json"
_HEADERS = {"User-Agent": "ACE-advising-bot/1.0 (Penn State student advising tool)"}

CATEGORIES = [
    "dining", "housing", "library", "recreation", "health", "transit",
    "parking", "it_printing", "study_space", "mail",
]

# Live-hours pages, kept separate from the records so the service can always
# point at the authoritative page instead of a stored time.
HOURS_URLS = {
    "dining": "https://liveon.psu.edu/university-park/dining/location-hours",
    "library": "https://libraries.psu.edu/hours-and-locations",
    "recreation": "https://studentaffairs.psu.edu/health-wellbeing/recreation",
}

# (url, category hint)
SOURCES = [
    # Dining
    ("https://liveon.psu.edu/university-park/dining/location-hours", "dining"),
    ("https://liveon.psu.edu/university-park/dining", "dining"),
    ("https://liveon.psu.edu/university-park/dining/east-food-district", "dining"),
    ("https://liveon.psu.edu/university-park/dining/north-food-district", "dining"),
    ("https://liveon.psu.edu/university-park/dining/fresco-pollock", "dining"),
    ("https://liveon.psu.edu/university-park/dining/south-food-district", "dining"),
    ("https://liveon.psu.edu/university-park/dining/west-food-district", "dining"),
    ("https://liveon.psu.edu/university-park/dining/hub-dining", "dining"),
    ("https://liveon.psu.edu/university-park/dining/more-dining-locations", "dining"),
    ("https://liveon.psu.edu/university-park/meal-plans", "dining"),
    # Housing
    ("https://liveon.psu.edu/university-park/housing-options", "housing"),
    ("https://liveon.psu.edu/university-park/undergraduate-housing", "housing"),
    ("https://liveon.psu.edu/university-park/rates", "housing"),
    ("https://liveon.psu.edu/university-park/summer", "housing"),
    ("https://liveon.psu.edu/university-park/current-students", "housing"),
    # Libraries and study space
    ("https://libraries.psu.edu/hours-and-locations", "library"),
    ("https://libraries.psu.edu/services/rooms-spaces", "study_space"),
    ("https://libraries.psu.edu/about/libraries", "library"),
    # Recreation
    ("https://studentaffairs.psu.edu/health-wellbeing/recreation", "recreation"),
    ("https://studentaffairs.psu.edu/health-wellbeing/recreation/programs-classes/aquatics", "recreation"),
    ("https://studentaffairs.psu.edu/health-wellbeing/recreation/programs-classes/competitive-sports", "recreation"),
    # Health
    ("https://studentaffairs.psu.edu/health-wellbeing/medical-services", "health"),
    ("https://studentaffairs.psu.edu/health-wellbeing/mental-health-services", "health"),
    # Transit and parking
    ("https://transportation.psu.edu", "transit"),
    ("https://transportation.psu.edu/parking", "parking"),
    ("https://transportation.psu.edu/student-parking", "parking"),
    ("https://transportation.psu.edu/parking-tickets", "parking"),
    ("https://transportation.psu.edu/accessible-parking", "parking"),
    # IT and printing. Note the www — the bare host returns a shell with no
    # content, which is why the first pass produced nothing here.
    ("https://www.it.psu.edu/labs/locations", "it_printing"),
    ("https://www.it.psu.edu/labs", "it_printing"),
    ("https://www.it.psu.edu/support", "it_printing"),
    ("https://www.it.psu.edu/wireless", "it_printing"),
    ("https://www.it.psu.edu/students/connect-to-tech", "it_printing"),
]

_EXTRACT_SYSTEM = (
    "You turn a university web page into structured records of PLACES and SERVICES "
    "a student physically uses. Extract ONLY what the page states. Never invent a "
    "building, address, phone number, or service. "
    "CRITICAL: do NOT extract opening hours or times as values — they change "
    "constantly and are handled separately. If the page gives hours, ignore them. "
    "Institutional phone numbers and office emails are fine; never include an "
    "individual person's contact details."
)

_SCHEMA_HINT = """Return JSON only, exactly this shape:
{"places": [
  {
    "name": "the place or service, e.g. 'Findlay Commons (East Food District)'",
    "category": "one of: %s",
    "what_it_is": "1-2 sentences a student would find useful",
    "where": "building, hall, or campus area if stated, else ''",
    "good_for": ["short tags, e.g. 'late night', 'group study', 'halal'"],
    "phone": "institutional phone if stated, else ''",
    "notes": "anything practical: how to access, what to bring, cost, else ''"
  }
]}
Return every distinct place the page describes. If the page is about one service,
return a single record. Return {"places": []} if there is nothing concrete.""" % ", ".join(CATEGORIES)


def fetch_text(url: str) -> tuple[str, str]:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=30)
        if r.status_code != 200:
            logger.warning("%s → HTTP %s", url, r.status_code)
            return "", ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s → %s", url, exc)
        return "", ""

    soup = BeautifulSoup(r.text, "html.parser")
    title = (soup.title.get_text(strip=True) if soup.title else "").split("|")[0].strip()
    for tag in soup(["script", "style", "nav", "header", "footer", "form"]):
        tag.decompose()
    main = soup.find("main") or soup.find(id="main-content") or soup.body
    if main is None:
        return title, ""
    return title, re.sub(r"\n{2,}", "\n", main.get_text("\n", strip=True))


def map_url(name: str, where: str) -> str:
    """A Google Maps SEARCH for the place at University Park.

    Deliberately a search, not a pin: ACE has no verified coordinates, and a
    search that lands near the right building is honest where a wrong pin is not.
    """
    query = f"{name} {where} Penn State University Park".strip()
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)


def extract_places(url: str, hint: str, title: str, text: str) -> list[dict]:
    from backend.services import llm

    prompt = (
        f"{_SCHEMA_HINT}\n\nLikely category: {hint}\nPage title: {title}\n"
        f"Page URL: {url}\n\nPage content:\n{text[:12000]}"
    )
    try:
        raw = llm.chat(
            [{"role": "system", "content": _EXTRACT_SYSTEM},
             {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            feature="places_extract",
        )
        data = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.error("extract failed for %s: %s", url, exc)
        return []

    out = []
    for place in data.get("places", []):
        name = (place.get("name") or "").strip()
        if not name or not place.get("what_it_is"):
            continue
        category = place.get("category") if place.get("category") in CATEGORIES else hint
        where = (place.get("where") or "").strip()
        out.append({
            "id": re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60],
            "name": name,
            "category": category,
            "what_it_is": place.get("what_it_is", ""),
            "where": where,
            "good_for": [g for g in place.get("good_for", []) if isinstance(g, str)][:6],
            "phone": (place.get("phone") or "").strip(),
            "notes": (place.get("notes") or "")[:400],
            "url": url,
            "map_url": map_url(name, where),
            "hours_url": HOURS_URLS.get(category, ""),
            "source_url": url,
        })
    return out


def build(limit=None) -> dict:
    sources = SOURCES[:limit] if limit else SOURCES
    places, seen = [], set()

    for url, hint in sources:
        title, text = fetch_text(url)
        if not text:
            continue
        found = extract_places(url, hint, title, text)
        logger.info("%s → %d place(s)", url, len(found))
        for place in found:
            key = (place["name"].lower(), place["category"])
            if key in seen:
                continue
            seen.add(key)
            places.append(place)
        time.sleep(0.3)

    return {
        "_about": (
            "Penn State campus places and services. Built by "
            "`python -m backend.data.places_scraper`. HOURS ARE DELIBERATELY NOT "
            "STORED — they change by term and by day; each record carries the live "
            "hours page instead. map_url is a Google Maps search, not a verified pin. "
            "LLM extraction is not bit-for-bit reproducible: diff before committing."
        ),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "count": len(places),
        "hours_urls": HOURS_URLS,
        "places": places,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Scrape Penn State campus places and services.")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=str(OUT_FILE))
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    from dotenv import load_dotenv
    load_dotenv()

    data = build(limit=args.limit)
    if not data["places"]:
        print("Nothing extracted — refusing to overwrite places.json.")
        return 1
    Path(args.out).write_text(
        json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {data['count']} places to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
