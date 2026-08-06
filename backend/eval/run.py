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

Judge scores drift between runs on the same answer — some items score anywhere
from 0.50 to 1.00 — so a single run cannot detect a small regression. `--runs 3`
answers and grades each item three times, averages, and flags any item whose
best and worst run differ by 0.3 or more as VOLATILE. A volatile item is not
evidence of anything; fix its expected_points or read it by hand.

Usage:
    python -m backend.eval.run                 # full run (hard asserts + judge)
    python -m backend.eval.run --runs 3        # 3-run average + volatility report
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

def collect_answer(question: str, major: str | None) -> tuple[str, str | None, dict]:
    """Run a question through the chat pipeline. Returns (text, error, visual).

    Consumes the SSE generator and concatenates the streamed text chunks. No
    user_id is passed, so no DB / uploaded-document context is involved — the
    major is supplied directly via the override parameter.

    The `visual` payload comes back too, because an answer now reaches the
    student through two channels. Grading only the text made the fix for the
    duplicated dining answer look like a regression: the directions links moved
    from six numbered prose bullets into the cards, which is exactly what was
    wanted, and a text-only assertion read that as information lost.
    """
    # Imported lazily so --help and unit tests don't pull in OpenAI/the index.
    from backend.services.chat_service import ask_advisor_stream

    text_parts: list[str] = []
    error: str | None = None
    visual: dict = {}
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
        if data.get("visual"):
            visual = data["visual"]
    return "".join(text_parts), error, visual


# ── Scoring ─────────────────────────────────────────────────────────────────

def check_hard_assertions(answer: str, item: dict, visual: dict | None = None) -> list[str]:
    """Return a list of human-readable failure messages (empty == all passed).

    Both channels count. A required link that reaches the student inside a
    rendered card has reached the student; a forbidden word hiding in a block
    payload has still leaked.
    """
    failures: list[str] = []
    rendered = json.dumps(visual or {})
    low = (answer + "\n" + rendered).lower()
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
    "Judge only against the expected points, not your own outside knowledge. "
    "The answer may arrive in two parts: prose, and a rendered block the student "
    "sees directly beneath it. Grade the WHOLE reply. A name or link that appears "
    "in the block has reached the student, and repeating it in the prose as well "
    "is duplication, not thoroughness — do not reward it."
)


def describe_block(visual: dict | None) -> str:
    """The rendered block, written out as the student experiences it.

    Without this the judge grades one channel of a two-channel answer. Moving the
    dining list out of the prose and into cards — the whole point of the block —
    scored 0.00 on three items for "does not name specific organisations", which
    the student was in fact looking straight at.
    """
    data = (visual or {}).get("data")
    if not data:
        return ""
    lines = [f"[{visual.get('block')} block, rendered directly beneath the prose]"]
    for item in data.get("items") or []:
        links = " ".join(l.get("url", "") for l in item.get("links") or [])
        lines.append(f"- {item.get('title','')} | {item.get('meta','')} | "
                     f"{item.get('body','')} | {links}".strip())
    for step in data.get("steps") or []:
        lines.append(f"- step: {step}")
    for f in data.get("facts") or []:
        lines.append(f"- {f['k']}: {f['v']}")
    for ev in data.get("events") or []:
        lines.append(f"- {ev.get('label','')} | {ev.get('date','')}")
    for term in data.get("terms") or []:
        for c in term.get("courses") or []:
            lines.append(f"- {c.get('code','')} {c.get('title','')}")
    if data.get("source"):
        lines.append(f"- source: {data['source']}")
    if data.get("hours_url"):
        lines.append(f"- live hours: {data['hours_url']}")
    return "\n".join(lines)


def build_judge_prompt(item: dict, answer: str, visual: dict | None = None) -> str:
    points = "\n".join(f"- {p}" for p in item.get("expected_points", []))
    block = describe_block(visual)
    return (
        f"Question:\n{item['question']}\n\n"
        f"Expected points a good answer should cover:\n{points or '(none specified)'}\n\n"
        f"Assistant's answer (prose):\n{answer}"
        + (f"\n\nAlso shown to the student:\n{block}" if block else "")
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


def judge_answer(item: dict, answer: str, visual: dict | None = None) -> tuple[float, str]:
    from backend.services import llm

    raw = llm.chat(
        [
            {"role": "system", "content": _JUDGE_SYSTEM},
            {"role": "user", "content": build_judge_prompt(item, answer, visual)},
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


def run_item(item, runs, judge_on):
    """Answer and grade one item `runs` times. Returns (answers, hards, scores, reasons).

    Each run REGENERATES the answer as well as re-judging it, because both are
    sources of variance and a student only ever experiences the pair. Judging one
    frozen answer repeatedly would measure the grader and flatter the pipeline.
    """
    answers, hards, scores, reasons = [], [], [], []
    for _ in range(runs):
        answer, error, visual = collect_answer(item["question"], item.get("major"))
        hard = check_hard_assertions(answer, item, visual)
        if error:
            hard.append(f"pipeline error: {error}")
        answers.append(answer)
        hards.append(hard)

        if judge_on and not error:
            try:
                score, reason = judge_answer(item, answer, visual)
                scores.append(score)
                reasons.append(reason)
            except Exception as e:  # noqa: BLE001 — the judge must never crash a run
                reasons.append(f"judge error: {e}")
    return answers, hards, scores, reasons


def spread(scores):
    """(mean, min, max) or (None, None, None)."""
    if not scores:
        return None, None, None
    return sum(scores) / len(scores), min(scores), max(scores)


# A gap this wide between the best and worst run means one number tells you
# nothing — the item, not the pipeline, is what moved.
VARIANCE_FLAG = 0.3


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the ACE answer-quality eval.")
    ap.add_argument("--set", default=str(_DEFAULT_SET), help="path to eval set JSON")
    ap.add_argument("--no-judge", action="store_true", help="hard assertions only (no judge calls)")
    ap.add_argument("--filter", default=None, help="only items whose id or major contains this")
    ap.add_argument("--threshold", type=float, default=0.7, help="judge score below this is flagged")
    ap.add_argument("--runs", type=int, default=1, metavar="N",
                    help="answer and grade each item N times, and average "
                         "(3 is enough to stop chasing noise; costs N x the calls)")
    args = ap.parse_args()
    runs = max(1, args.runs)

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
    rows: list[dict] = []
    judge_on = not args.no_judge

    calls = len(items) * runs * (2 if judge_on else 1)
    print(f"Running {len(items)} eval item(s) x {runs} run(s) | model={OPENAI_CHAT_MODEL} "
          f"| judge={'on' if judge_on else 'off'} | ~{calls} model calls\n")

    for item in items:
        answers, hards, scores, reasons = run_item(item, runs, judge_on)

        # An item fails hard if ANY run fails. A must_not that holds two times in
        # three is not holding — that is exactly the leak worth catching.
        failed_runs = [h for h in hards if h]
        if failed_runs:
            hard_failures += 1
        mean, lo, hi = spread(scores)
        volatile = mean is not None and (hi - lo) >= VARIANCE_FLAG

        rows.append({"item": item, "hard": failed_runs, "mean": mean,
                     "lo": lo, "hi": hi, "volatile": volatile, "reasons": reasons})

        status = "FAIL" if failed_runs else "ok  "
        score_s = "  -  " if mean is None else f"{mean:.2f}"
        band = ""
        if mean is not None and runs > 1:
            band = f"  [{lo:.2f}–{hi:.2f}]{'  ⚠ volatile' if volatile else ''}"
        print(f"[{status}] {score_s}  {item['id']:<24} ({item.get('major','—')}){band}")
        for h in failed_runs:
            for f in h:
                print(f"          ✗ {f}")
        # One reason is enough when they agree; show each when the runs disagree.
        for reason in (reasons if volatile else reasons[:1]):
            if reason:
                print(f"          · {reason}")

    # ── Summary ──
    n = len(items)
    graded = [r for r in rows if r["mean"] is not None]
    print("\n" + "─" * 60)
    print(f"Hard assertions: {n - hard_failures}/{n} passed"
          + (f"  (an item fails if any of its {runs} runs fails)" if runs > 1 else ""))
    if graded:
        mean = sum(r["mean"] for r in graded) / len(graded)
        below = [r for r in graded if r["mean"] < args.threshold]
        print(f"Judge mean score: {mean:.2f} over {len(graded)} item(s)"
              + (f", averaged across {runs} runs" if runs > 1 else ""))
        print(f"Below threshold ({args.threshold}): {len(below)}")
        for r in below:
            print(f"  - {r['item']['id']} ({r['mean']:.2f})")

        volatile = [r for r in graded if r["volatile"]]
        if volatile:
            print(f"\nVolatile ({VARIANCE_FLAG:+.1f} or more between best and worst run): "
                  f"{len(volatile)}")
            for r in volatile:
                print(f"  - {r['item']['id']} [{r['lo']:.2f}–{r['hi']:.2f}]")
            print("  These items cannot detect a small regression. Tighten their "
                  "expected_points, or read the answers by hand.")
        elif runs > 1:
            print("\nNo volatile items — a change in the mean is worth believing.")

    # Non-zero exit on any hard failure so this is usable as a gate.
    return 1 if hard_failures else 0


if __name__ == "__main__":
    sys.exit(main())
