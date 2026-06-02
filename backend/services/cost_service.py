"""OpenAI API cost accounting for ACE.

Single source of truth for model pricing and per-call cost. Powers BOTH:
  • the live tracker — record_usage() logs real token usage (from each API
    response) to the api_usage table; summarize() aggregates it; and
  • the estimator — estimate() projects spend from assumptions.

Prices are USD per 1,000,000 tokens. Update when OpenAI changes pricing.
"""
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# USD per 1M tokens. Only models ACE uses are billed precisely; others are
# listed so a model swap is costed correctly without code changes.
PRICING = {
    "gpt-4o-mini":            {"input": 0.15, "cached_input": 0.075, "output": 0.60},
    "gpt-4o":                 {"input": 2.50, "cached_input": 1.25,  "output": 10.00},
    "gpt-4.1":                {"input": 2.00, "cached_input": 0.50,  "output": 8.00},
    "gpt-4.1-mini":           {"input": 0.40, "cached_input": 0.10,  "output": 1.60},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
}


def cost_usd(model, input_tokens=0, output_tokens=0, cached_input_tokens=0):
    """USD cost for one call. Unknown models cost 0 (logged, not billed)."""
    p = PRICING.get(model)
    if not p:
        return 0.0
    cached = cached_input_tokens or 0
    uncached = max(0, (input_tokens or 0) - cached)
    return (
        uncached * p.get("input", 0.0)
        + cached * p.get("cached_input", p.get("input", 0.0))
        + (output_tokens or 0) * p.get("output", 0.0)
    ) / 1_000_000


def _field(usage, *names):
    for n in names:
        v = usage.get(n) if isinstance(usage, dict) else getattr(usage, n, None)
        if v is not None:
            return v
    return 0


def tokens_from_usage(usage):
    """(input, output, cached) from an OpenAI usage object or dict."""
    if usage is None:
        return 0, 0, 0
    inp = _field(usage, "prompt_tokens", "input_tokens") or 0
    out = _field(usage, "completion_tokens", "output_tokens") or 0
    cached = 0
    details = (usage.get("prompt_tokens_details") if isinstance(usage, dict)
               else getattr(usage, "prompt_tokens_details", None))
    if details:
        cached = (details.get("cached_tokens") if isinstance(details, dict)
                  else getattr(details, "cached_tokens", 0)) or 0
    return int(inp), int(out), int(cached)


def record_usage(feature, model, usage, user_id=None):
    """Persist one call's tokens + computed cost. Best-effort: never raises
    into the caller — cost logging must not break a chat or a search."""
    try:
        from backend.database import SessionLocal
        from backend.models import ApiUsage
        inp, out, cached = tokens_from_usage(usage)
        cost = cost_usd(model, inp, out, cached)
        db = SessionLocal()
        try:
            db.add(ApiUsage(
                feature=feature, model=model,
                input_tokens=inp, output_tokens=out, cached_tokens=cached,
                cost_usd=cost, user_id=user_id,
            ))
            db.commit()
        finally:
            db.close()
        return cost
    except Exception as exc:  # noqa: BLE001 — logging must be non-fatal
        logger.warning("record_usage failed (%s/%s): %s", feature, model, exc)
        return 0.0


def summarize(db):
    """Aggregate recorded usage for the /admin/costs dashboard."""
    from backend.models import ApiUsage
    from sqlalchemy import func

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    month_ago = now - timedelta(days=30)

    def window(since):
        q = db.query(
            func.count(ApiUsage.id),
            func.coalesce(func.sum(ApiUsage.input_tokens), 0),
            func.coalesce(func.sum(ApiUsage.output_tokens), 0),
            func.coalesce(func.sum(ApiUsage.cost_usd), 0.0),
        )
        if since is not None:
            q = q.filter(ApiUsage.created_at >= since)
        calls, inp, out, cost = q.one()
        return {
            "calls": int(calls or 0),
            "input_tokens": int(inp or 0),
            "output_tokens": int(out or 0),
            "cost_usd": round(float(cost or 0.0), 4),
        }

    rows = (
        db.query(
            ApiUsage.feature, ApiUsage.model,
            func.count(ApiUsage.id),
            func.coalesce(func.sum(ApiUsage.cost_usd), 0.0),
        )
        .group_by(ApiUsage.feature, ApiUsage.model)
        .all()
    )
    breakdown = [
        {"feature": f, "model": m, "calls": int(c), "cost_usd": round(float(cost or 0.0), 4)}
        for (f, m, c, cost) in rows
    ]

    last_30 = window(month_ago)
    chat_calls_30 = (
        db.query(func.count(ApiUsage.id))
        .filter(ApiUsage.created_at >= month_ago, ApiUsage.feature == "chat")
        .scalar()
    ) or 0
    avg_per_chat = round(last_30["cost_usd"] / chat_calls_30, 6) if chat_calls_30 else 0.0

    return {
        "currency": "USD",
        "all_time": window(None),
        "last_30_days": last_30,
        "last_24_hours": window(day_ago),
        "by_feature_model": breakdown,
        "avg_cost_per_chat_message_usd": avg_per_chat,
        "projected_monthly_usd": round(last_30["cost_usd"], 2),
        "pricing_per_million_tokens": PRICING,
    }


def estimate(users, msgs_per_user_per_month,
             avg_input_tokens=3000, avg_output_tokens=450,
             chat_model="gpt-4o-mini",
             embed_model="text-embedding-3-small", avg_query_tokens=40):
    """Project monthly/annual spend from usage assumptions (no DB needed)."""
    total_messages = users * msgs_per_user_per_month
    per_chat = cost_usd(chat_model, avg_input_tokens, avg_output_tokens)
    per_embed = cost_usd(embed_model, avg_query_tokens, 0)
    per_message = per_chat + per_embed
    monthly = total_messages * per_message
    return {
        "currency": "USD",
        "inputs": {
            "users": users,
            "messages_per_user_per_month": msgs_per_user_per_month,
            "avg_input_tokens": avg_input_tokens,
            "avg_output_tokens": avg_output_tokens,
            "chat_model": chat_model,
            "embed_model": embed_model,
        },
        "total_messages_per_month": total_messages,
        "cost_per_message_usd": round(per_message, 6),
        "monthly_usd": round(monthly, 2),
        "annual_usd": round(monthly * 12, 2),
    }
