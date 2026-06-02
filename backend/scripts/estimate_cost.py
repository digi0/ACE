"""What-if OpenAI cost estimator for ACE — pure projection, no DB or server.

Usage:
  python -m backend.scripts.estimate_cost --users 500 --msgs 20
  python -m backend.scripts.estimate_cost --users 500 --msgs 20 --model gpt-4o
"""
import argparse

from backend.services.cost_service import estimate, PRICING


def main():
    ap = argparse.ArgumentParser(description="Estimate ACE's monthly OpenAI spend.")
    ap.add_argument("--users", type=int, required=True, help="active users")
    ap.add_argument("--msgs", type=float, required=True, help="chat messages per user per month")
    ap.add_argument("--in", dest="avg_in", type=int, default=3000, help="avg input tokens / message")
    ap.add_argument("--out", dest="avg_out", type=int, default=450, help="avg output tokens / message")
    ap.add_argument("--model", default="gpt-4o-mini", help=f"chat model: {', '.join(PRICING)}")
    args = ap.parse_args()

    r = estimate(args.users, args.msgs, args.avg_in, args.avg_out, chat_model=args.model)
    print(f"\nACE OpenAI cost estimate — chat model: {args.model}")
    print("─" * 44)
    print(f"  users                 : {args.users:,}")
    print(f"  messages/user/month   : {args.msgs:g}")
    print(f"  total messages/month  : {r['total_messages_per_month']:,.0f}")
    print(f"  cost per message      : ${r['cost_per_message_usd']:.6f}")
    print(f"  → projected monthly   : ${r['monthly_usd']:,.2f}")
    print(f"  → projected annual    : ${r['annual_usd']:,.2f}\n")


if __name__ == "__main__":
    main()
