"""Build visa.json — the F-1 provisions an international student does not know exist.

ACE's answer to every visa question was one sentence: "that's handled by your
international student adviser." Safe, and useless. A student about to drop below
full-time has FIVE authorised Reduced Course Load routes available to them and
almost certainly knows about none — so they drop the course, break status, and
find out afterwards.

This dataset is deliberately NOT immigration advice. It is the map: what
provisions exist, what conditions attach, WHAT BREAKS if you get it wrong, who
authorises it, and the exact question to walk into ISSA with. ACE names the
options; only a DSO can tell a student which one applies to them.

The `risk_if_wrong` field is the point. A "loopholes" dataset would list the
opportunity and omit the danger, and dropping to 6 credits without authorisation
is out of status THAT DAY. Every record carries both halves or it is not safe to
serve.

Source is Penn State Global (global.psu.edu), which is server-rendered plain
HTML — no Firecrawl needed, so this can run from cron where an MCP connection
does not exist. Extraction is an LLM pass (gpt-4o-mini, temperature 0, strict
JSON), so it is not bit-for-bit reproducible: diff before committing.

    python -m backend.data.visa_scraper
    python -m backend.data.visa_scraper --limit 3   # sample run
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

OUT_FILE = Path(__file__).parent / "visa.json"
_HEADERS = {"User-Agent": "ACE-advising-bot/1.0 (Penn State student advising tool)"}

# What a student's situation lands on. Blunt on purpose — the service matches
# against these, they are not a taxonomy of immigration law.
TOPICS = [
    "full_time_enrollment", "reduced_course_load", "on_campus_work", "cpt",
    "opt", "stem_opt", "travel", "i20", "transfer", "status_violation",
    "grace_period", "program_change", "ssn", "documents", "insurance",
]

# (url, topic hint). F-1 undergraduate essentials — the questions a Penn State
# international undergrad actually arrives with. J-1 is a different mental model
# and is deliberately out of this first pass.
SOURCES = [
    # The rule everything else hangs off.
    ("https://global.psu.edu/article/enrollment-requirements", "full_time_enrollment"),
    ("https://global.psu.edu/page/f-1-regulations", "full_time_enrollment"),
    ("https://global.psu.edu/page/requesting-reduced-course-load", "reduced_course_load"),
    # Working — the biggest source of accidental violations.
    ("https://global.psu.edu/page/f-1-campus-employment", "on_campus_work"),
    ("https://global.psu.edu/page/f-1-curricular-practical-training-cpt", "cpt"),
    ("https://global.psu.edu/landing/post-completion-opt", "opt"),
    ("https://global.psu.edu/page/pre-completion-opt", "opt"),
    ("https://global.psu.edu/page/cap-gap-extension", "opt"),
    ("https://global.psu.edu/landing/unpaid-work", "cpt"),
    ("https://global.psu.edu/landing/employment-f-1-international-students", "on_campus_work"),
    ("https://global.psu.edu/page/f-1-severe-economic-hardship", "on_campus_work"),
    # When something has already gone wrong.
    ("https://global.psu.edu/page/activities-may-impact-your-immigration-status", "status_violation"),
    ("https://global.psu.edu/page/correcting-terminated-f-1-record", "status_violation"),
    ("https://global.psu.edu/page/taking-break-studies", "status_violation"),
    # Documents, travel, and the clock.
    ("https://global.psu.edu/page/international-travel-and-travel-signature", "travel"),
    ("https://global.psu.edu/page/f-1-i-20-extension", "i20"),
    ("https://global.psu.edu/page/completing-your-studies", "grace_period"),
    ("https://global.psu.edu/page/transferring-new-institution", "transfer"),
    ("https://global.psu.edu/page/lost-or-stolen-documents", "documents"),
    # Life admin that still touches status.
    ("https://global.psu.edu/page/change-major", "program_change"),
    ("https://global.psu.edu/page/change-academic-level", "program_change"),
    ("https://global.psu.edu/page/social-security-number", "ssn"),
    ("https://global.psu.edu/page/health-insurance", "insurance"),
    ("https://global.psu.edu/page/updating-address-and-contact-information", "documents"),
]

_EXTRACT_SYSTEM = (
    "You turn one Penn State international-student page into structured records "
    "for an advising assistant. Extract ONLY what the page states — never add a "
    "rule, a number, a deadline or an eligibility condition that is not written "
    "there. Immigration guidance that is invented can put a student out of "
    "status.\n\n"
    "A page often describes SEVERAL distinct provisions (the Reduced Course Load "
    "page has five separate approved reasons, each with its own conditions and "
    "credit minimum). Emit one record per PROVISION, not one per page.\n\n"
    "risk_if_wrong is the most important field and must never be empty when the "
    "page says anything about consequences. A student reading only the "
    "opportunity and not the danger is the failure this dataset exists to "
    "prevent: dropping below full-time WITHOUT authorisation is a status "
    "violation immediately, not a paperwork problem.\n\n"
    "ask_adviser is the question the student should put to their international "
    "student adviser. It must NOT be a yes/no restatement of the title — 'Can I "
    "request a reduced course load?' is useless, because the student already "
    "knows that is what they want. Ask the thing that decides it: 'I used "
    "academic-difficulty RCL in my first semester — can I use a different reason "
    "now?', 'Does my thesis defence term count as my final semester for the "
    "I-20 end date?'. ACE cannot tell a student whether they qualify; it can "
    "send them in knowing the question that settles it.\n\n"
    "numbers must capture every limit the page states, including maximums and "
    "durations ('limited to a maximum of 12 months total', 'once per degree "
    "program'), not just credit counts.\n\n"
    "who_authorises is the office that APPROVES this, as the page names it. Use "
    "the page's own name for the office — do not substitute an acronym you know "
    "from elsewhere. Never name an individual staff member."
)

_SCHEMA_HINT = """Return JSON only, exactly this shape:
{
  "records": [
    {
      "title": "short, e.g. 'Reduced Course Load - Medical or Psychological'",
      "topic": "one of: %s",
      "what_it_is": "1-2 sentences: what this provision allows",
      "when_it_applies": "the student situation this is for",
      "conditions": ["each eligibility condition or limit the page states"],
      "numbers": ["credit minimums, durations, deadlines, hour caps AS WRITTEN"],
      "risk_if_wrong": "what happens to status if done wrong or without authorisation",
      "who_authorises": "the office as the page names it",
      "how_to_start": "the first concrete action the student takes",
      "ask_adviser": "the question to bring to their adviser",
      "side_effects": ["knock-on effects: tuition, aid, graduation timing"]
    }
  ]
}""" % ", ".join(TOPICS)


_ESCAPED = re.compile(r"\\u([0-9a-fA-F]{4})")


def _text_from_next_payload(html: str) -> str:
    """Readable text out of Next.js flight data.

    global.psu.edu server-renders its shell and ships the actual page body as
    JSON inside <script>, so the five Reduced Course Load reasons — the most
    valuable content on the site — were invisible to BeautifulSoup, which
    decomposes <script> before reading anything. The soup saw 3,276 characters
    and none of them mentioned "Academic Difficulty".

    The payload holds HTML with \\u003c escapes, so unescape and re-parse. Done
    here rather than by adding a JS-rendering dependency, because this has to run
    from cron where a browser does not.
    """
    out = []
    for m in re.finditer(r"<script[^>]*>(.*?)</script>", html, re.S):
        chunk = m.group(1)
        if "\\u003c" not in chunk:
            continue
        decoded = _ESCAPED.sub(lambda x: chr(int(x.group(1), 16)), chunk)
        decoded = decoded.replace("\\n", "\n").replace('\\"', '"')
        text = BeautifulSoup(decoded, "html.parser").get_text("\n", strip=True)
        if text:
            out.append(text)
    return re.sub(r"\n{2,}", "\n", "\n".join(out))


def fetch_text(url: str) -> tuple[str, str]:
    """(page_title, readable_text). ('', '') when the page can't be read."""
    try:
        r = requests.get(url, headers=_HEADERS, timeout=30)
        if r.status_code != 200:
            logger.warning("%s -> HTTP %s", url, r.status_code)
            return "", ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s -> %s", url, exc)
        return "", ""

    soup = BeautifulSoup(r.text, "html.parser")
    title = (soup.title.get_text(strip=True) if soup.title else "").split("|")[0].strip()
    for tag in soup(["script", "style", "nav", "header", "footer", "form"]):
        tag.decompose()
    main = soup.find("main") or soup.find(id="content") or soup.body
    visible = re.sub(r"\n{2,}", "\n", main.get_text("\n", strip=True)) if main else ""

    # Whichever actually carries the page. On this site the payload wins by an
    # order of magnitude; on a plain HTML page it is empty and `visible` wins.
    payload = _text_from_next_payload(r.text)
    return title, payload if len(payload) > len(visible) else visible


def extract_records(url: str, topic_hint: str, title: str, text: str) -> list[dict]:
    """Every provision on one page. [] when extraction fails."""
    from backend.services import llm

    prompt = (
        f"{_SCHEMA_HINT}\n\nLikely topic: {topic_hint}\n"
        f"Page title: {title}\nPage URL: {url}\n\nPage content:\n{text[:14000]}"
    )
    try:
        raw = llm.chat(
            [{"role": "system", "content": _EXTRACT_SYSTEM},
             {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            feature="visa_extract",
        )
        data = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.error("extract failed for %s: %s", url, exc)
        return []

    out = []
    for rec in data.get("records", []):
        if not isinstance(rec, dict) or not rec.get("what_it_is"):
            continue
        topic = rec.get("topic") if rec.get("topic") in TOPICS else topic_hint
        name = rec.get("title") or title
        out.append({
            "id": re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60],
            "title": name,
            "topic": topic,
            "visa": "F-1",
            "what_it_is": rec.get("what_it_is", ""),
            "when_it_applies": rec.get("when_it_applies", ""),
            "conditions": [c for c in rec.get("conditions", []) if isinstance(c, str)][:10],
            "numbers": [n for n in rec.get("numbers", []) if isinstance(n, str)][:10],
            "risk_if_wrong": rec.get("risk_if_wrong", ""),
            "who_authorises": rec.get("who_authorises", ""),
            "how_to_start": rec.get("how_to_start", ""),
            "ask_adviser": rec.get("ask_adviser", ""),
            "side_effects": [s for s in rec.get("side_effects", []) if isinstance(s, str)][:6],
            "source_url": url,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build visa.json from Penn State Global.")
    ap.add_argument("--limit", type=int, help="only the first N sources (sampling)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    sources = SOURCES[: args.limit] if args.limit else SOURCES
    records, seen, failed = [], set(), []
    for url, hint in sources:
        title, text = fetch_text(url)
        if not text:
            failed.append(url)
            continue
        got = extract_records(url, hint, title, text)
        if not got:
            failed.append(url)
        for rec in got:
            if rec["id"] in seen:
                continue
            seen.add(rec["id"])
            records.append(rec)
        logger.info("%-62s -> %d record(s)", url.split("/")[-1][:62], len(got))

    no_risk = [r["id"] for r in records if not r["risk_if_wrong"]]
    if no_risk:
        logger.warning("%d record(s) have no risk_if_wrong: %s", len(no_risk), no_risk[:5])

    OUT_FILE.write_text(json.dumps({
        "_about": (
            "Penn State F-1 provisions — what exists, what it requires, and what "
            "breaks if you get it wrong. Built by `python -m backend.data.visa_scraper` "
            "from global.psu.edu. NOT immigration advice: ACE names the options and "
            "the question to ask; only a DSO at Penn State Global can tell a student "
            "which applies to them. LLM extraction is not bit-for-bit reproducible — "
            "diff before committing."
        ),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "sources_failed": failed,
        "records": records,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    logger.info("wrote %s records to %s (%d source(s) failed)",
                len(records), OUT_FILE.name, len(failed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
