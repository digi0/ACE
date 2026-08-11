"""Per-person invite codes on the waitlist.

Guarded the same way 0001 and 0002 are, for the same reason: prod already has
this table with ten real signups in it, and a migration that fails at boot is a
deploy that does not come back.

Revision ID: 0003_waitlist_invite_codes
Revises: 0002_profile_rating_usage
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_waitlist_invite_codes"
down_revision: Union[str, None] = "0002_profile_rating_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    if not _has_column("waitlist", "access_code"):
        op.add_column("waitlist", sa.Column("access_code", sa.String(32), nullable=True))
        # Unique as an index rather than a column constraint, so it can be added
        # to a populated table without a rewrite, and so NULL stays repeatable
        # for everyone not yet invited.
        op.create_index("ix_waitlist_access_code", "waitlist", ["access_code"], unique=True)
    if not _has_column("waitlist", "redeemed_at"):
        op.add_column("waitlist", sa.Column("redeemed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    if _has_column("waitlist", "redeemed_at"):
        op.drop_column("waitlist", "redeemed_at")
    if _has_column("waitlist", "access_code"):
        op.drop_index("ix_waitlist_access_code", table_name="waitlist")
        op.drop_column("waitlist", "access_code")
