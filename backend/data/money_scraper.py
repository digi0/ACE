"""Build money.json — the navigational half of student money.

The playbook's Money surface is "financial aid, the bursar, scholarships,
work-study, refunds, what that charge is, who to email about it". ACE already
refuses financial-aid ADVICE, correctly and deliberately — eligibility and
borrowing are high-liability and belong to the Office of Student Aid. But it was
also refusing to answer "who do I email about this charge", which is not advice.
It is navigation, and navigation is the entire product.

So this dataset is scoped hard:

  IN  — how billing works, where the bill lives, how to pay, how refunds are
        issued, what a late fee is, which office owns which question, and the
        phone numbers and forms to reach them.
  OUT — anything about one student's own aid: eligibility, award amounts, what
        to borrow, whether to take a loan, what they personally owe. The service
        that reads this file re-states that boundary in the prompt.

Source: bursar.psu.edu, plain HTML.

    python -m backend.data.money_scraper
    python -m backend.data.money_scraper --limit 3
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

OUT_FILE = Path(__file__).parent / "money.json"
_HEADERS = {"User-Agent": "ACE-advising-bot/1.0 (Penn State student advising tool)"}

TOPICS = [
    "billing", "payments", "refunds", "late_fees", "holds", "contacts",
    "forms", "third_party", "new_students",
]

SOURCES = [
    # "Who do I email about this charge" — the question that prompted this set.
    ("https://www.bursar.psu.edu/contact-us", "contacts"),
    ("https://www.bursar.psu.edu/news/who-reach-out-questions-about-your-student-account-and-financial-aid", "contacts"),
    # Billing and paying.
    ("https://www.bursar.psu.edu", "billing"),
    ("https://www.bursar.psu.edu/tuition-due-dates", "billing"),
    ("https://www.bursar.psu.edu/fees", "billing"),
    ("https://www.bursar.psu.edu/make-payment", "payments"),
    ("https://www.bursar.psu.edu/payment-options", "payments"),
    ("https://www.bursar.psu.edu/new-billing-portal-updates", "billing"),
    # Refunds.
    ("https://www.bursar.psu.edu/refund-policy", "refunds"),
    ("https://www.bursar.psu.edu/faq/why-have-i-not-received-my-refund", "refunds"),
    ("https://www.bursar.psu.edu/faq/what-erefund-and-how-do-i-enroll-erefund", "refunds"),
    ("https://www.bursar.psu.edu/faq/how-do-i-get-refund-credit-balance-my-account", "refunds"),
    # What happens when you don't pay.
    ("https://www.bursar.psu.edu/delinquent-tuition", "late_fees"),
    ("https://www.bursar.psu.edu/faq/what-happens-if-i-do-not-pay-my-student-account-balance-due-date", "late_fees"),
    # Everything else a student trips over.
    ("https://www.bursar.psu.edu/student-account-forms", "forms"),
    ("https://www.bursar.psu.edu/sponsored-third-party-billing", "third_party"),
    ("https://www.bursar.psu.edu/international-students", "new_students"),
    ("https://www.bursar.psu.edu/new-student-information", "new_students"),
    ("https://www.bursar.psu.edu/faq/can-i-pay-credit-card", "payments"),
]

_EXTRACT_SYSTEM = (
    "You turn a university bursar page into one structured record for a student "
    "advising assistant. Extract ONLY what the page states — never invent a fee, "
    "a deadline, an office, a phone number, or a step. "
    "This record is for NAVIGATION: how billing works and who to contact. Do NOT "
    "extract anything that reads as advice about an individual student's financial "
    "aid, borrowing, or eligibility. Institutional phone numbers and office email "
    "addresses are wanted; an individual person's contact details are not.\n"
    "who_to_contact is the office that OWNS this page and this process. A page may "
    "mention another office as a possible cause or a related step — that belongs in "
    "notes, never in who_to_contact. A bursar page is owned by the Bursar even when "
    "it mentions financial aid; sending a student to the wrong office is the most "
    "expensive mistake this record can make."
)

# Built by concatenation, not %-formatting: the example value contains a literal
# "1.5%" and percent-formatting choked on it.
_SCHEMA_HINT = (
    "Return JSON only, exactly this shape:\n"
    "{\n"
    '  "title": "short human title, e.g. \'Getting a refund of a credit balance\'",\n'
    '  "topic": "one of: ' + ", ".join(TOPICS) + '",\n'
    '  "what_it_is": "1-2 sentences",\n'
    '  "steps": ["ordered actions the student takes, if the page gives any"],\n'
    '  "who_to_contact": "the office, with phone or email if stated, else \'\'",\n'
    '  "amounts": ["stated fees or rates, quoted exactly, e.g. \'1.5% late fee\'"],\n'
    '  "timing": "stated deadlines or processing times, else \'\'",\n'
    '  "notes": "anything else practical, else \'\'"\n'
    "}"
)


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


def extract_record(url: str, hint: str, title: str, text: str) -> dict | None:
    from backend.services import llm

    prompt = (f"{_SCHEMA_HINT}\n\nLikely topic: {hint}\nPage title: {title}\n"
              f"Page URL: {url}\n\nPage content:\n{text[:12000]}")
    try:
        raw = llm.chat(
            [{"role": "system", "content": _EXTRACT_SYSTEM},
             {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            feature="money_extract",
        )
        data = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.error("extract failed for %s: %s", url, exc)
        return None

    if not data.get("what_it_is") and not data.get("steps"):
        return None

    topic = data.get("topic") if data.get("topic") in TOPICS else hint
    return {
        "id": re.sub(r"[^a-z0-9]+", "-", (data.get("title") or title).lower()).strip("-")[:60],
        "title": data.get("title") or title,
        "topic": topic,
        "what_it_is": data.get("what_it_is", ""),
        "steps": [s for s in data.get("steps", []) if isinstance(s, str)][:10],
        "who_to_contact": data.get("who_to_contact", ""),
        "amounts": [a for a in data.get("amounts", []) if isinstance(a, str)][:8],
        "timing": data.get("timing", ""),
        "notes": (data.get("notes") or "")[:400],
        "source_url": url,
        "source_title": title,
    }


def build(limit=None) -> dict:
    sources = SOURCES[:limit] if limit else SOURCES
    records, seen = [], set()
    for url, hint in sources:
        title, text = fetch_text(url)
        if not text:
            continue
        logger.info("extracting %s (%d chars)", url, len(text))
        record = extract_record(url, hint, title, text)
        if not record:
            continue
        if record["id"] in seen:
            record["id"] = f"{record['id']}-{len(records)}"
        seen.add(record["id"])
        records.append(record)
        time.sleep(0.3)

    return {
        "_about": (
            "Penn State student-account navigation from bursar.psu.edu: how billing, "
            "payment, refunds and late fees work, and which office to contact. "
            "NAVIGATION ONLY — nothing here is advice about an individual student's "
            "financial aid, and money_service re-states that boundary in the prompt. "
            "Rebuild with `python -m backend.data.money_scraper`; LLM extraction is "
            "not bit-for-bit reproducible, so diff before committing."
        ),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "money": records,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Scrape Penn State bursar navigation.")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=str(OUT_FILE))
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    from dotenv import load_dotenv
    load_dotenv()

    data = build(limit=args.limit)
    if not data["money"]:
        print("Nothing extracted — refusing to overwrite money.json.")
        return 1
    Path(args.out).write_text(
        json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {data['count']} money records to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
