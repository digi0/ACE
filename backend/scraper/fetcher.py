"""
HTTP fetcher with local HTML caching and polite rate limiting.
"""

import hashlib
import logging
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://bulletins.psu.edu"
CACHE_DIR = Path(__file__).parent.parent / "data" / "raw_html"
REQUEST_DELAY = 1.2  # seconds between requests

HEADERS = {
    "User-Agent": (
        "PSU-ACE-Scraper/1.0 (Penn State academic advisor project; "
        "contact: student research tool)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

_session = requests.Session()
_session.headers.update(HEADERS)
_last_request_time: float = 0.0


def _cache_path(url: str) -> Path:
    """Stable filename derived from the URL."""
    key = hashlib.md5(url.encode()).hexdigest()
    # Also embed a readable slug for easier debugging
    slug = url.replace(BASE_URL, "").strip("/").replace("/", "_")[:60]
    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in slug)
    return CACHE_DIR / f"{slug}__{key}.html"


def fetch(url: str, *, force: bool = False) -> BeautifulSoup | None:
    """
    Fetch a URL and return parsed BeautifulSoup.
    Uses a file cache; set force=True to re-download.
    Returns None on failure (logs the error).
    """
    global _last_request_time

    if not url.startswith("http"):
        url = BASE_URL + url

    cache_file = _cache_path(url)

    if not force and cache_file.exists():
        logger.debug("Cache hit: %s", url)
        html = cache_file.read_text(encoding="utf-8")
        return BeautifulSoup(html, "html.parser")

    # Polite delay
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)

    try:
        logger.debug("Fetching: %s", url)
        resp = _session.get(url, timeout=20)
        resp.raise_for_status()
        _last_request_time = time.time()
    except requests.RequestException as exc:
        logger.warning("FETCH FAILED %s — %s", url, exc)
        return None

    html = resp.text
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(html, encoding="utf-8")

    return BeautifulSoup(html, "html.parser")
