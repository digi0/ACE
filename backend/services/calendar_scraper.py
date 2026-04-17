"""
Penn State Academic Calendar Scraper
=====================================
Fetches https://www.registrar.psu.edu/academic-calendars/2025-26.cfm and
saves structured JSON to backend/data/calendar.json.

Run standalone:
    python -m backend.services.calendar_scraper
"""

import json
import logging
import re
import sys
from datetime import date, datetime, timezone

UTC = timezone.utc
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

CALENDAR_URL   = "https://www.registrar.psu.edu/academic-calendars/2025-26.cfm"
CALENDAR_FILE  = Path(__file__).parent.parent / "data" / "calendar.json"

HEADERS = {
    "User-Agent": (
        "PSU-ACE-Bot/1.0 (Penn State academic advisor; student research tool)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Date helpers ───────────────────────────────────────────────────────────────

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

# Semester → year lookup (matches PSU 2025-26 calendar)
_SEMESTER_YEAR = {
    "fall 2025": 2025,
    "spring 2026": 2026,
    "summer 2026": 2026,
}


def _semester_year(semester_name: str) -> int:
    """Derive the calendar year from a semester heading."""
    lower = semester_name.lower()
    for key, yr in _SEMESTER_YEAR.items():
        if key in lower:
            return yr
    # Fallback: extract 4-digit year from the name
    m = re.search(r"\b(20\d\d)\b", semester_name)
    return int(m.group(1)) if m else datetime.now().year


def _parse_date_string(date_str: str, year: int) -> tuple[str | None, str | None]:
    """
    Parse a date string like:
      "Monday, January 12"
      "Friday, January 2 - Monday, January 26"   → use start date
      "Monday, January 19 at 11:59 p.m. (ET)"

    Returns (iso_date, time_str).  iso_date is "YYYY-MM-DD" or None.
    """
    if not date_str:
        return None, None

    # Split off time component
    time_str = None
    time_match = re.search(r"\bat\s+(.+)", date_str, re.I)
    if time_match:
        time_str = time_match.group(1).strip()
        date_str = date_str[: time_match.start()].strip()

    # Take only the start of a range ("X - Y" → "X")
    date_str = date_str.split(" - ")[0].strip()

    # Remove day-of-week prefix ("Monday, January 12" → "January 12")
    date_str = re.sub(r"^[A-Za-z]+,\s*", "", date_str).strip()

    # Parse "Month Day"
    m = re.match(r"([A-Za-z]+)\s+(\d+)", date_str)
    if not m:
        return None, time_str

    month_name = m.group(1).lower()
    day = int(m.group(2))
    month = MONTH_MAP.get(month_name)
    if not month:
        return None, time_str

    try:
        iso = date(year, month, day).isoformat()
    except ValueError:
        iso = None

    return iso, time_str


def _clean_event_name(h4: Tag) -> tuple[str, int | None]:
    """
    Extract the plain event name and footnote number from an <h4> tag.
    e.g. "Regular Drop - Deadline ¹"  →  ("Regular Drop - Deadline", 1)
    """
    # Collect footnote numbers from <sup>
    footnotes = [int(s.get_text(strip=True)) for s in h4.find_all("sup")
                 if s.get_text(strip=True).isdigit()]
    # Remove sups from name
    for sup in h4.find_all("sup"):
        sup.decompose()

    name = h4.get_text(" ", strip=True)
    # Normalise multiple spaces
    name = re.sub(r"\s{2,}", " ", name)
    return name, (footnotes[0] if footnotes else None)


# ── Main parse ─────────────────────────────────────────────────────────────────

def _parse_semester(header_div: Tag, content_div: Tag) -> dict:
    """
    Parse one semester's card-header + card-body into a structured dict.
    """
    # Semester name from h3 text
    h3 = header_div.find("h3")
    semester_name = h3.get_text(strip=True) if h3 else "Unknown Session"
    year = _semester_year(semester_name)

    # Footnote texts from the .footnotes block
    footnote_texts: dict[int, str] = {}
    fn_div = content_div.find("div", class_="footnotes")
    if fn_div:
        for sup in fn_div.find_all("sup"):
            num_text = sup.get_text(strip=True)
            if num_text.isdigit():
                num = int(num_text)
                sibling = sup.next_sibling
                text = sibling.strip() if sibling and isinstance(sibling, str) else ""
                footnote_texts[num] = text

    # Parse each list-group-item
    events: list[dict] = []
    for li in content_div.find_all("li", class_="list-group-item"):
        h4 = li.find("h4")
        p  = li.find("p")
        if not h4:
            continue

        event_name, footnote_num = _clean_event_name(h4)
        date_text = p.get_text(" ", strip=True) if p else ""

        # For ranges, also capture the end date
        end_iso = None
        if " - " in date_text:
            parts = date_text.split(" - ", 1)
            _, _ = _parse_date_string(parts[0].strip(), year)
            end_iso_candidate, _ = _parse_date_string(parts[1].strip(), year)
            end_iso = end_iso_candidate

        iso_date, time_str = _parse_date_string(date_text, year)

        event: dict = {
            "event":    event_name,
            "date":     date_text,
            "iso_date": iso_date,
        }
        if end_iso and end_iso != iso_date:
            event["end_iso_date"] = end_iso
        if time_str:
            event["time"] = time_str
        if footnote_num:
            fn_text = footnote_texts.get(footnote_num)
            event["footnote"] = fn_text or f"See footnote {footnote_num}"

        events.append(event)

    return {
        "semester": semester_name,
        "year": year,
        "events": events,
        "footnotes": footnote_texts,
    }


def _pick_current_semester(semesters: list[dict]) -> str:
    """
    Return the semester name that best matches today.
    - If today falls between a semester's first and last event date → that semester.
    - Else → the next upcoming semester (earliest start in the future).
    - Final fallback → the last semester in the list.
    """
    today = date.today()

    def semester_bounds(sem: dict) -> tuple[date | None, date | None]:
        dates = [
            date.fromisoformat(e["iso_date"])
            for e in sem["events"] if e.get("iso_date")
        ]
        return (min(dates), max(dates)) if dates else (None, None)

    # Check if today is inside any semester
    for sem in semesters:
        start, end = semester_bounds(sem)
        if start and end and start <= today <= end:
            return sem["semester"]

    # Otherwise find the next upcoming
    future = [
        (semester_bounds(s)[0], s)
        for s in semesters
        if semester_bounds(s)[0] and semester_bounds(s)[0] > today
    ]
    if future:
        future.sort(key=lambda x: x[0])
        return future[0][1]["semester"]

    return semesters[-1]["semester"] if semesters else ""


# ── Public scrape function ─────────────────────────────────────────────────────

def scrape_calendar(url: str = CALENDAR_URL) -> dict:
    """
    Scrape the registrar page and return the full calendar dict.
    Raises on network / parse error (caller decides whether to overwrite file).
    """
    logger.info("calendar_scraper: fetching %s", url)
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    semesters: list[dict] = []

    # Each semester is a Bootstrap card: .card-header + sibling .collapse div
    for header_div in soup.find_all("div", class_="card-header"):
        # The collapse target id comes from the button's data-target attribute
        btn = header_div.find("button", attrs={"data-target": True})
        if not btn:
            # Try the anchor link
            a = header_div.find("a", attrs={"data-target": True})
            btn = a
        if not btn:
            continue

        target_id = btn.get("data-target", "").lstrip("#")
        content_div = soup.find("div", id=target_id)
        if not content_div:
            continue

        try:
            sem = _parse_semester(header_div, content_div)
            if sem["events"]:
                semesters.append(sem)
                logger.info(
                    "calendar_scraper:   %s — %d events",
                    sem["semester"], len(sem["events"]),
                )
        except Exception as exc:
            logger.warning(
                "calendar_scraper: failed to parse %s: %s",
                header_div.get_text(strip=True)[:60], exc,
            )

    if not semesters:
        raise ValueError("No semester data found — page structure may have changed")

    current = _pick_current_semester(semesters)
    logger.info("calendar_scraper: current semester → %s", current)

    return {
        "scraped_at":        datetime.now(UTC).isoformat(),
        "source_url":        url,
        "current_semester":  current,
        "semesters":         semesters,
    }


def save_calendar(data: dict, path: Path = CALENDAR_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("calendar_scraper: saved %s", path)


def load_calendar(path: Path = CALENDAR_FILE) -> dict | None:
    """Load calendar.json from disk, return None if missing."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("calendar_scraper: could not read %s: %s", path, exc)
        return None


def refresh_calendar(url: str = CALENDAR_URL) -> dict:
    """
    Re-scrape and save. If the scrape fails and an existing file exists,
    keep the old file and re-raise.
    """
    try:
        data = scrape_calendar(url)
    except Exception as exc:
        logger.error("calendar_scraper: scrape failed (%s), keeping existing file", exc)
        raise

    save_calendar(data)
    return data


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        data = refresh_calendar()
        sem_names = [s["semester"] for s in data["semesters"]]
        print(f"Scraped {len(sem_names)} semesters:")
        for name in sem_names:
            print(f"  {name}")
        print(f"Current semester: {data['current_semester']}")
        print(f"Saved to: {CALENDAR_FILE}")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
