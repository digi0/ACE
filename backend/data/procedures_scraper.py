"""Build procedures.json — what a student actually DOES when something goes wrong.

The playbook's logistics surface is "registration windows, add/drop dates,
breaks, finals, tuition deadlines, holds on your account, what to do when you
miss one". ACE had the dates and none of the "what to do when you miss one".
A student who needs to retroactively drop a course after the deadline was being
handed a calendar.

Two sources, both plain HTML (no Firecrawl needed — this has to run from cron
later, where an MCP connection does not exist):

  registrar.psu.edu       — withdrawal, leave of absence, re-enrollment, grades,
                            registration mechanics, change of major/campus
  studentpetitions.psu.edu — the Faculty Senate petition process, which is how
                            anything retroactive actually happens

Each page is fetched, stripped to its content, and turned into one structured
record by an LLM extraction pass (gpt-4o-mini, temperature 0, strict JSON) —
the same approach policy_extractor.py already uses on the handbooks. Extraction
is not bit-for-bit reproducible, so diff the output before committing.

    python -m backend.data.procedures_scraper
    python -m backend.data.procedures_scraper --limit 3   # sample run
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

OUT_FILE = Path(__file__).parent / "procedures.json"
_HEADERS = {"User-Agent": "ACE-advising-bot/1.0 (Penn State student advising tool)"}

# Topics a student question can land on. Kept short and blunt — this is what the
# service matches against, not a taxonomy for its own sake.
TOPICS = [
    "withdrawal", "late_drop", "petition", "leave_of_absence", "re_enrollment",
    "grades", "registration", "change_program", "graduation", "transcripts",
    # Added after a real-situation test run: a student losing federal aid for
    # academic progress got routed to the aid office with no idea what had
    # happened to them or that an appeal existed, and a student on academic
    # warning was told an invented credit-overload policy.
    "aid_progress", "credit_overload",
]

# (url, topic hint). The hint seeds the extractor; it may correct it.
SOURCES = [
    # The retroactive path — the thing ACE could not answer at all.
    ("https://studentpetitions.psu.edu/student-petition-types", "petition"),
    ("https://studentpetitions.psu.edu/student-petition-process", "petition"),
    ("https://studentpetitions.psu.edu/petition-checklists", "petition"),
    ("https://studentpetitions.psu.edu/frequently-asked-questions", "petition"),
    ("https://studentpetitions.psu.edu/examples-of-appropriate-and-inappropriate-requests", "petition"),
    # Losing federal aid for academic progress — SAP. The single most
    # consequential financial event in an undergraduate's life, and ACE had no
    # knowledge of it at all.
    ("https://www.psu.edu/costs-aid/managing-aid/satisfactory-academic-progress", "aid_progress"),
    ("https://senate.psu.edu/students/policies-and-rules-for-undergraduate-students/appendix-e-financial-aid-satisfactory-academic-progress-policy/", "aid_progress"),
    # Credit overload — the 19-credit rule and what standing is required for it.
    ("https://bulletins.psu.edu/undergraduate/general-information/academic-information/registration-academic-records/credits/", "credit_overload"),
    ("https://www.registrar.psu.edu/registration/adding-dropping-auditing-courses.cfm", "credit_overload"),
    # Leaving, pausing, and coming back.
    ("https://www.registrar.psu.edu/enrollment/leaving/withdrawal.cfm", "withdrawal"),
    ("https://www.registrar.psu.edu/enrollment/leaving/leave-absence.cfm", "leave_of_absence"),
    ("https://www.registrar.psu.edu/enrollment/leaving/cancel-registration.cfm", "withdrawal"),
    ("https://www.registrar.psu.edu/enrollment/leaving/military-leave-absence-withdrawal-drop.cfm", "leave_of_absence"),
    ("https://www.registrar.psu.edu/enrollment/returning/reenrollment", "re_enrollment"),
    ("https://www.registrar.psu.edu/student-forms/academic-renewal.cfm", "re_enrollment"),
    # Course mechanics.
    ("https://www.registrar.psu.edu/registration/adding-dropping-auditing-courses.cfm", "late_drop"),
    ("https://www.registrar.psu.edu/registration/late-registration.cfm", "registration"),
    ("https://www.registrar.psu.edu/registration/registration-timetable.cfm", "registration"),
    ("https://www.registrar.psu.edu/registration/enforced-prerequisites.cfm", "registration"),
    ("https://www.registrar.psu.edu/registration/multiple-campus-registration.cfm", "registration"),
    # Grades.
    ("https://www.registrar.psu.edu/grades/grade-forgiveness.cfm", "grades"),
    ("https://www.registrar.psu.edu/grades/deferred-grades.cfm", "grades"),
    ("https://www.registrar.psu.edu/grades/satisfactory-unsatisfactory-grades.cfm", "grades"),
    ("https://www.registrar.psu.edu/grades/credit-examination.cfm", "grades"),
    # Programme and finishing.
    ("https://www.registrar.psu.edu/degree-planning/change-major.cfm", "change_program"),
    ("https://www.registrar.psu.edu/degree-planning/change-campus", "change_program"),
    ("https://www.registrar.psu.edu/graduation/intent.cfm", "graduation"),
    ("https://www.registrar.psu.edu/transcripts", "transcripts"),
    ("https://www.registrar.psu.edu/academic-progress", "grades"),
]

_EXTRACT_SYSTEM = (
    "You turn a university procedure page into one structured record for a student "
    "advising assistant. Extract ONLY what the page says — never add a step, a "
    "deadline, an office, or a form that is not written there. If the page does not "
    "state something, use an empty string or empty list. Prefer the page's own "
    "wording for rules. Steps must be the actions a STUDENT takes, in order, and "
    "concrete enough to follow. For who_to_contact, name the OFFICE and never an "
    "individual staff member — a named person goes stale, and a personal name does "
    "not belong in a file ACE quotes into answers.\n\n"
    "WATCH FOR PAIRED OPPOSING LISTS. Some pages put 'X MAY include' and "
    "'NOT considered X' side by side, and a flattened read merges them into "
    "one list — which inverts the meaning. On the SAP appeals page this would "
    "tell a student that 'time management issues' is a valid appeal reason "
    "when it is explicitly refused, and appeals cannot be re-filed on the same "
    "reason. If you cannot tell which list an item belongs to, put it in "
    "NEITHER and say so in consequences. who_to_contact is the office "
    "that OWNS this page and this process, not every office the page mentions. A "
    "petitions page is owned by the petitions office even when it warns you that a "
    "petition affects your aid; offices mentioned as a consequence or an aside "
    "belong in consequences or notes. This mattered: 'Student Petition Types' came "
    "back owned by the Office of Student Aid, so ACE sent a student filing a "
    "retroactive withdrawal to the wrong building."
)

_SCHEMA_HINT = """Return JSON only, exactly this shape:
{
  "title": "short human title, e.g. 'Retroactive late course drop'",
  "topic": "one of: %s",
  "what_it_is": "1-2 sentences: what this procedure is",
  "when_to_use": "1-2 sentences: the situation a student would be in",
  "steps": ["ordered actions the student takes"],
  "timing": "deadlines or timing rules stated on the page, else ''",
  "forms": ["names of forms or documents required"],
  "who_to_contact": "the office or person the page says to go to, else ''",
  "consequences": "what it does to the transcript, aid, or degree progress, else ''",
  "policy_refs": ["Penn State policy numbers mentioned, e.g. 34-89"]
}""" % ", ".join(TOPICS)


def fetch_text(url: str) -> tuple[str, str]:
    """(page_title, readable_text). ('', '') when the page can't be read."""
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
    main = soup.find("main") or soup.find(id="content") or soup.body
    if main is None:
        return title, ""
    text = main.get_text("\n", strip=True)
    return title, re.sub(r"\n{2,}", "\n", text)


def extract_record(url: str, topic_hint: str, title: str, text: str) -> dict | None:
    """One structured procedure from one page. None when extraction fails."""
    from backend.services import llm

    prompt = (
        f"{_SCHEMA_HINT}\n\nLikely topic: {topic_hint}\n"
        f"Page title: {title}\nPage URL: {url}\n\nPage content:\n{text[:12000]}"
    )
    try:
        raw = llm.chat(
            [{"role": "system", "content": _EXTRACT_SYSTEM},
             {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            feature="procedures_extract",
        )
        data = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.error("extract failed for %s: %s", url, exc)
        return None

    if not data.get("what_it_is") and not data.get("steps"):
        logger.warning("empty extraction for %s — skipping", url)
        return None

    topic = data.get("topic")
    if topic not in TOPICS:
        topic = topic_hint

    return {
        "id": re.sub(r"[^a-z0-9]+", "-", (data.get("title") or title).lower()).strip("-")[:60],
        "title": data.get("title") or title,
        "topic": topic,
        "what_it_is": data.get("what_it_is", ""),
        "when_to_use": data.get("when_to_use", ""),
        "steps": [s for s in data.get("steps", []) if isinstance(s, str)][:12],
        "timing": data.get("timing", ""),
        "forms": [f for f in data.get("forms", []) if isinstance(f, str)][:8],
        "who_to_contact": data.get("who_to_contact", ""),
        "consequences": data.get("consequences", ""),
        "policy_refs": [p for p in data.get("policy_refs", []) if isinstance(p, str)][:6],
        "source_url": url,
        "source_title": title,
    }


def build(limit=None, sources=None) -> dict:
    sources = sources or (SOURCES[:limit] if limit else SOURCES)
    records, seen_ids = [], set()

    for url, hint in sources:
        title, text = fetch_text(url)
        if not text:
            continue
        logger.info("extracting %s (%d chars)", url, len(text))
        record = extract_record(url, hint, title, text)
        if not record:
            continue
        if record["id"] in seen_ids:
            record["id"] = f"{record['id']}-{len(records)}"
        seen_ids.add(record["id"])
        records.append(record)
        time.sleep(0.3)

    return {
        "_about": (
            "Penn State student procedures — what to do when something goes wrong or "
            "off-schedule. Built by `python -m backend.data.procedures_scraper` from "
            "registrar.psu.edu and studentpetitions.psu.edu. LLM extraction is not "
            "bit-for-bit reproducible: diff before committing."
        ),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "procedures": records,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Scrape Penn State student procedures.")
    ap.add_argument("--limit", type=int, default=None, help="only the first N sources")
    ap.add_argument("--only", nargs="+", metavar="URLFRAGMENT",
                    help="scrape only sources matching these fragments and MERGE")
    ap.add_argument("--out", default=str(OUT_FILE))
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    from dotenv import load_dotenv
    load_dotenv()

    if args.only:
        # Scrape ONLY these URLs and merge into what is already on disk. A full
        # re-run rewrites all 25 records, which would have silently reverted the
        # hand-corrected "Student Petition Types" office — that record pointed
        # students at the Office of Student Aid for a petition, and the fix was
        # made by a human reading the sibling page. Verified corrections must
        # survive adding a new source.
        wanted = set(args.only)
        subset = [(u, t) for (u, t) in SOURCES if any(w in u for w in wanted)]
        if not subset:
            print(f"No source matches {args.only}")
            return 1
        fresh = build(sources=subset)
        existing = json.loads(Path(args.out).read_text(encoding="utf-8"))
        by_id = {r["id"]: r for r in existing["procedures"]}
        added = [r for r in fresh["procedures"] if r["id"] not in by_id]
        by_id.update({r["id"]: r for r in fresh["procedures"]})
        data = {**existing, "procedures": list(by_id.values())}
        data["count"] = len(data["procedures"])
        data["scraped_at"] = fresh["scraped_at"]
        print(f"merged: {len(added)} new, {len(fresh['procedures']) - len(added)} updated, "
              f"{len(existing['procedures'])} preserved")
    else:
        data = build(limit=args.limit)
    if not data["procedures"]:
        print("Nothing extracted — refusing to overwrite procedures.json.")
        return 1
    Path(args.out).write_text(
        json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {data['count']} procedures to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
