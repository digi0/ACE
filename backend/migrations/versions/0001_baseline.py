"""Baseline: the schema as it stood before Alembic existed.

Adopting Alembic on a database that is already live has one hard problem — this
revision must be a no-op on prod, where every one of these tables already holds
real rows, while still building the whole schema on a fresh checkout. The usual
answer is `alembic stamp head` run by hand against prod. That needs someone to
remember, at exactly the right moment, and it is silent when they forget.

So every step asks the database what it already has. Prod skips all of it and
records the revision; a new SQLite file gets the lot. Nothing to remember.

Revision ID: 0001_baseline
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    have = _existing_tables()

    if "users" not in have:
        op.create_table(
            "users",
            sa.Column("id", sa.String(256), primary_key=True),
            sa.Column("email", sa.String(320), nullable=True),
            sa.Column("display_name", sa.String(256), nullable=True),
            sa.Column("selected_major", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("last_login", sa.DateTime(), nullable=True),
        )

    if "user_docs" not in have:
        op.create_table(
            "user_docs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.String(256),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("filename", sa.String(512), nullable=True),
            sa.Column("doc_type", sa.String(64), nullable=True),
            sa.Column("text", sa.Text(), nullable=True),
            sa.Column("analysis_json", sa.Text(), nullable=True),
            sa.Column("audit_parse_json", sa.Text(), nullable=True),
            sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_user_docs_user_id", "user_docs", ["user_id"])

    if "conversations" not in have:
        op.create_table(
            "conversations",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(256),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(512), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    if "messages" not in have:
        op.create_table(
            "messages",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("conversation_id", sa.String(64),
                      sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(16), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("intent", sa.String(64), nullable=True),
            sa.Column("sources_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    if "waitlist" not in have:
        op.create_table(
            "waitlist",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("email", sa.String(320), nullable=False, unique=True),
            sa.Column("major", sa.String(500), nullable=True),
            sa.Column("referral", sa.String(120), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("invited_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_waitlist_created_at", "waitlist", ["created_at"])


def downgrade() -> None:
    # Deliberately not implemented. Downgrading the baseline means dropping every
    # table a live product has, and an ALEMBIC TYPO should not be able to do that.
    raise NotImplementedError("the baseline is not reversible on purpose")
