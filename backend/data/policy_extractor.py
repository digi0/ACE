"""
Handbook Policy Extractor
=========================
Turns the CMPSC / DTSCE advising handbook PDFs into structured
`backend/data/policies.json` — the procedural rules (Entrance to Major,
petitions, substitutions, contacts, internships, honors, graduation) that
programs.json / courses.json do not carry.

This is the structured replacement for reading those handbooks through RAG.
It runs as a build step, like the scrapers — never at request time.

Run standalone:
    python -m backend.data.policy_extractor              # extract both handbooks
    python -m backend.data.policy_extractor --dry-run    # print, do not write
    python -m backend.data.policy_extractor --pages 6    # pages per model call

Pipeline (one pass per handbook):
    extract_pdf_pages()  →  page batches  →  gpt-4o-mini (strict JSON schema)
                         →  merge + dedupe + stable ids  →  policies.json
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from backend.config import (
    HANDBOOK_FILE, HANDBOOK_SOURCE_NAME, HANDBOOK_SOURCE_LINK,
    DS_HANDBOOK_FILE, DS_HANDBOOK_SOURCE_NAME, DS_HANDBOOK_SOURCE_LINK,
    OPENAI_CHAT_MODEL,
)
from backend.data.pdf_ingestor import extract_pdf_pages

load_dotenv()
logger = logging.getLogger(__name__)

POLICIES_FILE = Path(__file__).parent / "policies.json"
PAGES_PER_CALL = 4

# `scope` matches classify_major() in chat_service.py; `topic` matches
# detect_question_intent() where an intent exists, so relaying is a lookup.
TOPICS = [
    "etm", "substitution", "transfer", "contact", "courses",
    "petition", "advising", "internship", "honors", "graduation", "general",
]

HANDBOOKS = [
    {
        "path": HANDBOOK_FILE,
        "scope": "cs",
        "program": "Computer Science, B.S.",
        "document": HANDBOOK_SOURCE_NAME,
        "link": HANDBOOK_SOURCE_LINK,
    },
    {
        "path": DS_HANDBOOK_FILE,
        "scope": "ds",
        "program": "Data Sciences, B.S.",
        "document": DS_HANDBOOK_SOURCE_NAME,
        "link": DS_HANDBOOK_SOURCE_LINK,
    },
]

POLICY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["policies"],
    "properties": {
        "policies": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["topic", "title", "statement", "details", "courses", "pages"],
                "properties": {
                    "topic": {"type": "string", "enum": TOPICS},
                    "title": {"type": "string"},
                    "statement": {
                        "type": "string",
                        "description": "The rule in one or two sentences, in the handbook's own words where possible.",
                    },
                    "details": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Supporting specifics: thresholds, deadlines, steps, named offices.",
                    },
                    "courses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Course codes the policy names, e.g. 'CMPSC 121'. Empty if none.",
                    },
                    "pages": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Handbook page numbers this policy came from.",
                    },
                },
            },
        }
    },
}

SYSTEM_PROMPT = """You extract advising POLICIES from a Penn State department handbook.

A policy is a rule, requirement, procedure, threshold, or contact a student must
act on — Entrance to Major criteria, GPA thresholds, petition and substitution
procedures, transfer-credit rules, internship/honors eligibility, graduation
steps, and who to email for what.

Rules:
- Extract only what the page text states. Never infer, generalize, or fill gaps.
- Quote the handbook's own wording in `statement` wherever you can.
- Keep every number exactly as written: GPAs, credit windows, deadlines, grades.
- One policy per distinct rule. Do not merge unrelated rules into one entry.
- Skip prose that is not actionable: welcome letters, mission statements,
  course catalog listings, and the suggested academic plan (those already live
  in the structured programs.json / courses.json data).
- If a page batch contains no policy, return an empty list."""


def _client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60]


def _batch_pages(pages, size):
    for i in range(0, len(pages), size):
        yield pages[i:i + size]


def extract_from_batch(client, handbook, batch):
    """One model call over a few handbook pages → list of policy dicts."""
    page_text = "\n\n".join(
        f"--- PAGE {p['page_number']} ---\n{p['text']}" for p in batch
    )
    user_prompt = (
        f"Handbook: {handbook['document']} (program: {handbook['program']})\n\n"
        f"{page_text}"
    )

    response = client.chat.completions.create(
        model=OPENAI_CHAT_MODEL,
        temperature=0.0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "policies", "strict": True, "schema": POLICY_SCHEMA},
        },
    )
    payload = json.loads(response.choices[0].message.content)
    return payload.get("policies", []), response.usage


def extract_handbook(client, handbook, pages_per_call=PAGES_PER_CALL):
    if not Path(handbook["path"]).exists():
        logger.warning("Handbook not found at %r — skipping", handbook["path"])
        return [], 0, 0

    pages = extract_pdf_pages(handbook["path"])
    logger.info("%s | %d pages → %d model calls",
                handbook["document"], len(pages), -(-len(pages) // pages_per_call))

    policies, prompt_tokens, completion_tokens = [], 0, 0
    for batch in _batch_pages(pages, pages_per_call):
        found, usage = extract_from_batch(client, handbook, batch)
        if usage:
            prompt_tokens += usage.prompt_tokens
            completion_tokens += usage.completion_tokens
        logger.info("  pages %s → %d policies",
                    f"{batch[0]['page_number']}-{batch[-1]['page_number']}", len(found))
        for p in found:
            p["scope"] = handbook["scope"]
            p["program"] = handbook["program"]
            p["source"] = {
                "document": handbook["document"],
                "link": handbook["link"],
                "pages": sorted(set(p.pop("pages", []))),
            }
            policies.append(p)

    return policies, prompt_tokens, completion_tokens


def dedupe(policies):
    """Collapse policies the model reported twice across page batches.

    Keyed on (scope, topic, normalized title); the longer statement wins and the
    page lists merge, so a rule split across a batch boundary keeps both pages.
    """
    merged = {}
    for p in policies:
        key = (p["scope"], p["topic"], _slug(p["title"]))
        existing = merged.get(key)
        if existing is None:
            merged[key] = p
            continue
        if len(p["statement"]) > len(existing["statement"]):
            p["source"]["pages"] = sorted(set(existing["source"]["pages"]) | set(p["source"]["pages"]))
            p["details"] = existing["details"] if len(existing["details"]) > len(p["details"]) else p["details"]
            merged[key] = p
        else:
            existing["source"]["pages"] = sorted(set(existing["source"]["pages"]) | set(p["source"]["pages"]))

    out = []
    for (scope, topic, slug), p in merged.items():
        p["policy_id"] = f"{scope}-{topic}-{slug}"
        out.append(p)

    out.sort(key=lambda p: (p["scope"], TOPICS.index(p["topic"]), p["policy_id"]))
    return out


def build(pages_per_call=PAGES_PER_CALL):
    client = _client()
    all_policies, prompt_tokens, completion_tokens = [], 0, 0

    for handbook in HANDBOOKS:
        found, pt, ct = extract_handbook(client, handbook, pages_per_call)
        all_policies.extend(found)
        prompt_tokens += pt
        completion_tokens += ct

    policies = dedupe(all_policies)

    # gpt-4o-mini: $0.15 / 1M prompt, $0.60 / 1M completion
    cost = prompt_tokens / 1e6 * 0.15 + completion_tokens / 1e6 * 0.60
    logger.info("Extracted %d policies (%d before dedupe) | %d prompt + %d completion tokens | ~$%.4f",
                len(policies), len(all_policies), prompt_tokens, completion_tokens, cost)

    return {
        "_about": (
            "Structured advising policies extracted from the CMPSC/DTSCE handbook PDFs by "
            "backend/data/policy_extractor.py. `scope` matches classify_major() and `topic` "
            "matches detect_question_intent(), so policy_service.py can relay them by intent "
            "without a retrieval step. Regenerate whenever the handbook PDFs change: "
            "python -m backend.data.policy_extractor"
        ),
        "model": OPENAI_CHAT_MODEL,
        "sources": [
            {"document": h["document"], "link": h["link"], "scope": h["scope"]}
            for h in HANDBOOKS if Path(h["path"]).exists()
        ],
        "policy_count": len(policies),
        "policies": policies,
    }


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print the result, do not write")
    parser.add_argument("--pages", type=int, default=PAGES_PER_CALL, help="handbook pages per model call")
    args = parser.parse_args()

    data = build(pages_per_call=args.pages)

    if args.dry_run:
        json.dump(data, sys.stdout, indent=2)
        print()
        return

    POLICIES_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote %d policies to %s", data["policy_count"], POLICIES_FILE)


if __name__ == "__main__":
    main()
