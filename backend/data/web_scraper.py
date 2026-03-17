import logging
import re

import httpx
from bs4 import BeautifulSoup

from backend.data.pdf_ingestor import chunk_text

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "ACE-Advisor-Bot/1.0 (PSU Academic Advisor)"}


def _table_to_text(table):
    """Convert an HTML table to pipe-delimited plain text rows."""
    rows = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
        if any(c.strip() for c in cells):
            rows.append("  |  ".join(cells))
    return "\n".join(rows)


def _extract_text(soup):
    """Strip boilerplate, convert tables to text, return clean body text."""
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Preserve table content as structured text before get_text strips it
    for table in soup.find_all("table"):
        table.replace_with(BeautifulSoup(_table_to_text(table) + "\n", "html.parser"))

    main = (
        soup.find("main")
        or soup.find("div", {"id": "main-content"})
        or soup.find("div", {"id": "main"})
        or soup.find("article")
        or soup.body
    )
    raw = main.get_text(separator=" ", strip=True) if main else ""
    return re.sub(r"\s+", " ", raw).strip()


def fetch_web_chunks(url, source_name, source_type="web_bulletin"):
    """Fetch *url*, extract meaningful text, and return chunked records.

    Returns an empty list (graceful degradation) if the fetch fails.
    """
    logger.info("Fetching web content | source_type=%r url=%r", source_type, url)
    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            response = client.get(url, headers=_HEADERS)
            response.raise_for_status()
    except Exception as e:
        logger.error("Web fetch failed | url=%r error=%s", url, e)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    text = _extract_text(soup)

    if not text:
        logger.warning("No text extracted | url=%r", url)
        return []

    chunks = chunk_text(text)
    records = []

    for i, chunk in enumerate(chunks, start=1):
        records.append({
            "record_id": f"web_{source_type}_{i}",
            "source_type": source_type,
            "source_name": source_name,
            "Title": source_name,
            "Category": "web",
            "Subcategory": "",
            "Used_for": "",
            "Content": chunk.strip(),
            "Source_link": url,
        })

    logger.info("Web scrape complete | source_type=%r chunks=%d", source_type, len(records))
    return records
