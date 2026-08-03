"""ACE answer-quality eval runner.

Runs each question in eval_set.json through the real chat pipeline
(ask_advisor_stream) with the item's selected major, then scores the answer
two ways:

  1. Hard assertions  — exact substring checks (must_contain / must_not),
     case-insensitive. Deterministic and free. A failure here is a real bug
     (e.g. a Psychology answer mentioning "CMPSC"), so any hard failure makes
     the runner exit non-zero (CI-friendly).

  2. LLM judge        — gpt-4o-mini scores the answer 0-1 against the item's
     expected_points. Captures quality/nuance that substring checks can't.
     Skipped with --no-judge.

Usage:
    python -m backend.eval.run                 # full run (hard asserts + judge)
    python -m backend.eval.run --no-judge      # hard asserts only (no judge cost)
    python -m backend.eval.run --filter psych  # only items whose id/major matches
    python -m backend.eval.run --set path.json # use a different eval set

Requires OPENAI_API_KEY (the answer generation always calls the chat model;
the judge adds one more call per item). Cost is small on gpt-4o-mini.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from backend.config import OPENAI_CHAT_MODEL

_DEFAULT_SET = Path(__file__).parent / "eval_set.json"
_JUDGE_MODEL = OPENAI_CHAT_MODEL  # judge with the same cheap model


# ── Pipeline ────────────────────────────────────────────────────────────────

def collect_answer(question: str, major: str | None) -> tuple[str, str | None]:
    """Run a question through the chat pipeline and return (answer_text, error).

    Consumes the SSE generator and concatenates the streamed text chunks. No
    user_id is passed, so no DB / uploaded-document context is involved — the
    major is supplied directly via the override parameter.
    """
    # Imported lazily so --help and unit tests don't pull in OpenAI/the index.
    from backend.services.chat_service import ask_advisor_stream

    text_parts: list[str] = []
    error: str | None = None
    for chunk in ask_advisor_stream(question, history=[], user_id=None, major=major):
        if not chunk.startswith("data: "):
            continue
        try:
            data = json.loads(chunk[6:].strip())
        except json.JSONDecodeError:
            continue
        if data.get("text"):
            text_parts.append(data["text"])
        if data.get("error"):
            error = data["error"]
    return "".join(text_parts), error


# ── Scoring ─────────────────────────────────────────────────────────────────

def check_hard_assertions(answer: str, item: dict) -> list[str]:
    """Return a list of human-readable failure messages (empty == all passed)."""
    failures: list[str] = []
    low = answer.lower()
    for needle in item.get("must_contain", []):
        if needle.lower() not in low:
            failures.append(f'missing required substring: "{needle}"')
    for needle in item.get("must_not", []):
        if needle.lower() in low:
            failures.append(f'contains forbidden substring: "{needle}"')
    if not answer.strip():
        failures.append("empty answer")
    return failures


_JUDGE_SYSTEM = (
    "You are a strict grader for an academic-advising assistant. Given a student "
    "question, a list of points a good answer should cover, and the assistant's "
    "answer, score how well the answer satisfies the expected points. Respond with "
    'JSON only: {"score": <float 0..1>, "reason": "<one sentence>"}. '
    "1.0 = fully covers every expected point accurately; 0.0 = misses them or is wrong. "
    "Judge only against the expected points, not your own outside knowledge."
)


def build_judge_prompt(item: dict, answer: str) -> str:
    points = "\n".join(f"- {p}" for p in item.get("expected_points", []))
    return (
        f"Question:\n{item['question']}\n\n"
        f"Expected points a good answer should cover:\n{points or '(none specified)'}\n\n"
        f"Assistant's answer:\n{answer}"
    )


def parse_judge_response(raw: str) -> tuple[float, str]:
    """Parse the judge's JSON; tolerate stray prose around it."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            return 0.0, f"unparseable judge response: {raw[:80]!r}"
        try:
            data = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return 0.0, f"unparseable judge response: {raw[:80]!r}"
    try:
        score = max(0.0, min(1.0, float(data.get("score", 0.0))))
    except (TypeError, ValueError):
        score = 0.0
    return score, str(data.get("reason", ""))[:200]


def judge_answer(item: dict, answer: str) -> tuple[float, str]:
    from backend.services import llm

    raw = llm.chat(
        [
            {"role": "system", "content": _JUDGE_SYSTEM},
            {"role": "user", "content": build_judge_prompt(item, answer)},
        ],
        response_format={"type": "json_object"},
        feature="eval_judge",
    )
    return parse_judge_response(raw)


# ── Runner ──────────────────────────────────────────────────────────────────

def load_items(path: Path, filt: str | None) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["items"] if isinstance(data, dict) else data
    if filt:
        f = filt.lower()
        items = [it for it in items if f in it["id"].lower() or f in (it.get("major") or "").lower()]
    return items


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the ACE answer-quality eval.")
    ap.add_argument("--set", default=str(_DEFAULT_SET), help="path to eval set JSON")
    ap.add_argument("--no-judge", action="store_true", help="hard assertions only (no judge calls)")
    ap.add_argument("--filter", default=None, help="only items whose id or major contains this")
    ap.add_argument("--threshold", type=float, default=0.7, help="judge score below this is flagged")
    args = ap.parse_args()

    # Load the repo-root .env so OPENAI_API_KEY is available even when it isn't
    # exported in the shell (chat_service also calls this, but we check the key
    # before importing it).
    from dotenv import load_dotenv
    load_dotenv()

    items = load_items(Path(args.set), args.filter)
    if not items:
        print("No eval items matched.")
        return 1

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set — the eval calls the chat model.")
        return 2

    hard_failures = 0
    scores: list[float] = []
    rows: list[dict] = []

    print(f"Running {len(items)} eval item(s) | model={OPENAI_CHAT_MODEL} | judge={'off' if args.no_judge else 'on'}\n")

    for item in items:
        answer, error = collect_answer(item["question"], item.get("major"))
        hard = check_hard_assertions(answer, item)
        if error:
            hard.append(f"pipeline error: {error}")
        if hard:
            hard_failures += 1

        score, reason = (None, "")
        if not args.no_judge and not error:
            try:
                score, reason = judge_answer(item, answer)
                scores.append(score)
            except Exception as e:  # noqa: BLE001 — judge must never crash the run
                reason = f"judge error: {e}"

        rows.append({"item": item, "hard": hard, "score": score, "reason": reason})

        status = "FAIL" if hard else "ok  "
        score_s = "  -  " if score is None else f"{score:.2f}"
        print(f"[{status}] {score_s}  {item['id']:<24} ({item.get('major','—')})")
        for f in hard:
            print(f"          ✗ {f}")
        if reason and not args.no_judge:
            print(f"          · {reason}")

    # ── Summary ──
    n = len(items)
    print("\n" + "─" * 60)
    print(f"Hard assertions: {n - hard_failures}/{n} passed")
    if scores:
        mean = sum(scores) / len(scores)
        below = [r for r in rows if r["score"] is not None and r["score"] < args.threshold]
        print(f"Judge mean score: {mean:.2f} over {len(scores)} item(s)")
        print(f"Below threshold ({args.threshold}): {len(below)}")
        for r in below:
            print(f"  - {r['item']['id']} ({r['score']:.2f})")

    # Non-zero exit on any hard failure so this is usable as a gate.
    return 1 if hard_failures else 0


if __name__ == "__main__":
    sys.exit(main())
