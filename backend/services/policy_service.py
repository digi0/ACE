"""
Policy relay
============
Serves the structured handbook policies in `backend/data/policies.json`
(built by `backend/data/policy_extractor.py`) into chat answers.

No retrieval, no embeddings: `scope` matches classify_major() and `topic`
matches detect_question_intent(), so selecting the right policies for a
question is a dict lookup.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

POLICIES_FILE = Path(__file__).parent.parent / "data" / "policies.json"
MAX_POLICIES_IN_SNIPPET = 8

# intent (detect_question_intent) → policy topics, most relevant first.
# Several topics per intent on purpose: the extractor files a rule under one
# topic, and near-synonyms ("advising" vs "graduation" for degree-audit rules)
# land differently across the two handbooks.
INTENT_TOPICS = {
    "etm":              ["etm", "transfer"],
    "transfer":         ["transfer", "etm"],
    "substitution":     ["substitution", "petition", "courses"],
    "contact":          ["contact", "advising"],
    "courses":          ["courses", "petition", "advising"],
    "student_progress": ["graduation", "advising"],
    "deadline":         ["petition", "graduation"],
    "general":          ["advising", "general", "graduation"],
}

_cache = None


def load_policies() -> dict:
    """Read policies.json once. A missing file is survivable — the RAG path and
    structured program data still answer; we just lose the policy snippet."""
    global _cache
    if _cache is not None:
        return _cache

    if not POLICIES_FILE.exists():
        logger.warning("policies.json not found at %r — run "
                       "`python -m backend.data.policy_extractor`", POLICIES_FILE)
        _cache = {"policies": [], "sources": []}
        return _cache

    _cache = json.loads(POLICIES_FILE.read_text(encoding="utf-8"))
    logger.info("Loaded %d handbook policies", len(_cache.get("policies", [])))
    return _cache


def get_policies(scope: str | None, topics: list[str] | None = None) -> list[dict]:
    """Policies for a scope ('cs' | 'ds'), optionally filtered to topics and
    ordered by the topic list so the most on-point rule leads."""
    if not scope:
        return []

    policies = [p for p in load_policies().get("policies", []) if p.get("scope") == scope]
    if topics is None:
        return policies

    ranked = []
    for topic in topics:
        ranked.extend(p for p in policies if p.get("topic") == topic)
    return ranked


def _format_policy(policy: dict) -> str:
    source = policy.get("source", {})
    pages = ", ".join(str(p) for p in source.get("pages", []))
    lines = [f"[{policy['topic'].upper()}] {policy['title']}", f"  {policy['statement']}"]
    for detail in policy.get("details", []):
        lines.append(f"  - {detail}")
    if policy.get("courses"):
        lines.append(f"  Courses named: {', '.join(policy['courses'])}")
    lines.append(f"  Source: {source.get('document', 'handbook')}"
                 + (f" p.{pages}" if pages else ""))
    return "\n".join(lines)


def build_policy_snippet(intent: str, scope: str | None) -> str:
    """The prompt block for a question's intent. Empty string when the student's
    major has no handbook (every major except CS/DS) or nothing matches."""
    topics = INTENT_TOPICS.get(intent)
    if not topics:
        return ""

    policies = get_policies(scope, topics)[:MAX_POLICIES_IN_SNIPPET]
    if not policies:
        return ""

    header = (
        "\n\n=== DEPARTMENT HANDBOOK POLICIES (structured) ===\n"
        "(Authoritative for procedure questions — Entrance to Major, petitions, "
        "substitutions, transfer credit, contacts. Quote these exactly; never "
        "round or restate a GPA, credit window, or deadline.)\n"
    )
    return header + "\n\n".join(_format_policy(p) for p in policies)


def policy_sources(scope: str | None) -> list[dict]:
    """Citation entries for the handbook a scope's policies came from.

    Labels match build_sources() in chat_service so the UI shows one consistent
    name for the handbook whether the answer came from RAG or from a policy.
    """
    if not scope:
        return []
    label = "DTSCE Handbook" if scope == "ds" else "CMPSC Handbook"
    return [
        {"title": label, "link": s["link"]}
        for s in load_policies().get("sources", [])
        if s.get("scope") == scope and s.get("link")
    ]
