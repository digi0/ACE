"""Turn real student questions into eval items.

The eval set started simulated. Once students are using ACE, the questions worth
regression-testing are the ones it got *wrong*: answers a student thumbed down,
and answers that landed with no sources behind them. This harvests those from the
messages table and writes them into the eval set.

    python -m backend.eval.from_transcripts                 # dry run — print only
    python -m backend.eval.from_transcripts --write         # append to eval_set.json
    python -m backend.eval.from_transcripts --days 30 --write

Expected points are drafted from the QUESTION ONLY, never from the answer ACE
gave — grading an answer against itself would bake the failure in as the
expectation. Drafted items carry "_drafted": true; read them before trusting a
score, and delete the flag once a human has checked the points.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.models import Conversation, Message, User

_DEFAULT_SET = Path(__file__).parent / "eval_set.json"

_DRAFT_SYSTEM = (
    "You write evaluation criteria for an academic-advising assistant at Penn State. "
    "Given a student's question (and their major, if known), list 2-3 short, checkable "
    "points a good answer must cover. Judge the QUESTION only — you have not seen any "
    "answer. Be concrete (e.g. 'names specific course codes', 'points to the registrar's "
    "academic calendar'). Respond with JSON only: {\"points\": [\"...\", \"...\"]}"
)


def normalize(question: str) -> str:
    """Loose key for dedupe — case and punctuation shouldn't make a new item."""
    return re.sub(r"[^a-z0-9 ]", "", (question or "").lower()).strip()


def harvest(db, days=7, limit=25):
    """Down-rated and ungrounded exchanges from the last `days`, newest first.

    Returns dicts of {question, major, intent, reason, answer}.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(Message, User.selected_major)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(User, Conversation.user_id == User.id)
        .filter(Message.role == "assistant", Message.created_at >= since)
        .filter(
            (Message.rating == -1)
            | (Message.sources_json == "[]")
            | (Message.sources_json.is_(None))
        )
        .order_by(Message.id.desc())
        .limit(limit * 4)  # room to drop the ones with no question row
        .all()
    )

    out = []
    for msg, major in rows:
        question = (
            db.query(Message)
            .filter(
                Message.conversation_id == msg.conversation_id,
                Message.role == "user",
                Message.id < msg.id,
            )
            .order_by(Message.id.desc())
            .first()
        )
        if not question:
            continue
        out.append({
            "question": question.content,
            "major": major,
            "intent": msg.intent,
            "reason": "rated_down" if msg.rating == -1 else "ungrounded",
            "answer": msg.content,
        })
        if len(out) >= limit:
            break
    return out


def draft_points(question, major):
    """LLM-drafted expected_points for one question. [] if the call fails."""
    from backend.services import llm

    prompt = f"Student question: {question}\nMajor: {major or 'not declared'}"
    try:
        raw = llm.chat(
            [
                {"role": "system", "content": _DRAFT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            feature="eval_draft",
        )
        points = json.loads(raw).get("points", [])
        return [str(p) for p in points][:3]
    except Exception as exc:  # noqa: BLE001 — a draft failure shouldn't kill the run
        print(f"  ! draft failed ({exc}) — leaving expected_points empty")
        return []


def make_item(row, existing_ids, points):
    """Build one eval item with an id that doesn't collide."""
    base = f"real-{row['intent'] or 'general'}"
    item_id, n = base, 1
    while item_id in existing_ids:
        n += 1
        item_id = f"{base}-{n}"
    existing_ids.add(item_id)

    item = {
        "id": item_id,
        "major": row["major"],
        "intent": row["intent"],
        "question": row["question"],
        "expected_points": points,
        "must_not": [],
        "_source": row["reason"],
        "_drafted": True,
    }
    # A structured-only major must never be answered with CS/DS material — the
    # same guard the hand-written items use.
    if row["major"] and not re.search(r"computer science|data sciences", row["major"], re.I):
        item["must_not"] = ["CMPSC", "DTSCE"]
    return item


def main() -> int:
    ap = argparse.ArgumentParser(description="Harvest real student questions into the eval set.")
    ap.add_argument("--set", default=str(_DEFAULT_SET), help="eval set to append to")
    ap.add_argument("--days", type=int, default=7, help="how far back to look")
    ap.add_argument("--limit", type=int, default=25, help="max items to harvest")
    ap.add_argument("--write", action="store_true", help="write to the eval set (default: dry run)")
    ap.add_argument("--no-draft", action="store_true", help="skip LLM-drafted expected_points")
    args = ap.parse_args()

    from dotenv import load_dotenv
    load_dotenv()

    from backend.database import SessionLocal

    path = Path(args.set)
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["items"] if isinstance(data, dict) else data
    seen = {normalize(i["question"]) for i in items}
    ids = {i["id"] for i in items}

    db = SessionLocal()
    try:
        rows = harvest(db, days=args.days, limit=args.limit)
    finally:
        db.close()

    fresh = [r for r in rows if normalize(r["question"]) not in seen]
    print(f"{len(rows)} candidate exchange(s) in the last {args.days} day(s); "
          f"{len(fresh)} new after dedupe.\n")
    if not fresh:
        return 0

    new_items = []
    for row in fresh:
        seen.add(normalize(row["question"]))
        points = [] if args.no_draft else draft_points(row["question"], row["major"])
        item = make_item(row, ids, points)
        new_items.append(item)
        print(f"[{item['_source']:<10}] {item['id']:<20} ({row['major'] or '—'})")
        print(f"   Q: {row['question'][:100]}")
        for p in points:
            print(f"   · {p}")

    if not args.write:
        print(f"\nDry run — pass --write to append {len(new_items)} item(s) to {path}.")
        return 0

    items.extend(new_items)
    if isinstance(data, dict):
        data["items"] = items
    else:
        data = items
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nAppended {len(new_items)} item(s) to {path}. Review the drafted "
          f"expected_points before trusting a score.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
