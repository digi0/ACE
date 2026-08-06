"""What this branch added: the student profile, answer ratings, api_usage.

Every step is guarded, because three different databases arrive at this revision
from three different places:

  a fresh checkout       — 0001 just built the old shape; everything here is new
  Railway today          — the tables are live and _ensure_columns may ALREADY
                           have added rating, profile_json and the index at boot
                           on a previous deploy
  a local dev SQLite     — same as Railway, for the same reason

An unguarded ADD COLUMN would fail on two of those three, and a failed migration
at boot is a deploy that does not come back up.

Revision ID: 0002_profile_rating_usage
Revises: 0001_baseline
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_profile_rating_usage"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_column(table: str, column: str) -> bool:
    insp = _inspector()
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def _has_index(table: str, index: str) -> bool:
    insp = _inspector()
    if table not in insp.get_table_names():
        return False
    return index in {i["name"] for i in insp.get_indexes(table)}


def upgrade() -> None:
    if not _has_column("users", "profile_json"):
        op.add_column("users", sa.Column("profile_json", sa.Text(), nullable=True))

    if not _has_column("messages", "rating"):
        op.add_column("messages", sa.Column("rating", sa.Integer(), nullable=True))

    # Drives the weekly review, which scans by recency. Missed the first time
    # round because create_all builds indexes only for tables it is creating —
    # so a fresh SQLite file had it and the long-running Postgres never did, and
    # local testing could not show the difference.
    if not _has_index("messages", "ix_messages_created_at"):
        op.create_index("ix_messages_created_at", "messages", ["created_at"])

    if "api_usage" not in _inspector().get_table_names():
        op.create_table(
            "api_usage",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("feature", sa.String(32), nullable=True),
            sa.Column("model", sa.String(64), nullable=True),
            sa.Column("input_tokens", sa.Integer(), nullable=True),
            sa.Column("output_tokens", sa.Integer(), nullable=True),
            sa.Column("cached_tokens", sa.Integer(), nullable=True),
            sa.Column("cost_usd", sa.Float(), nullable=True),
            sa.Column("user_id", sa.String(256), nullable=True),
        )
        op.create_index("ix_api_usage_created_at", "api_usage", ["created_at"])
        op.create_index("ix_api_usage_feature", "api_usage", ["feature"])


def downgrade() -> None:
    if "api_usage" in _inspector().get_table_names():
        op.drop_table("api_usage")
    if _has_index("messages", "ix_messages_created_at"):
        op.drop_index("ix_messages_created_at", table_name="messages")
    if _has_column("messages", "rating"):
        op.drop_column("messages", "rating")
    if _has_column("users", "profile_json"):
        op.drop_column("users", "profile_json")
