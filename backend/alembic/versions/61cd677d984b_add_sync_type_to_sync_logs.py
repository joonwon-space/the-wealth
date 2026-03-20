"""add sync_type to sync_logs and make user_id/portfolio_id nullable

Revision ID: a1b2c3d4e5f6
Revises: 3b36f89f99ca
Create Date: 2026-03-20 09:30:00.000000

Adds a sync_type column (default 'portfolio') to sync_logs to distinguish
portfolio sync events from system-level events such as db_backup.
Also makes user_id and portfolio_id nullable so system-level events
(that have no associated user or portfolio) can be recorded.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "61cd677d984b"
down_revision: Union[str, Sequence[str], None] = "3b36f89f99ca"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sync_type column with default 'portfolio' for backward compat
    op.add_column(
        "sync_logs",
        sa.Column(
            "sync_type",
            sa.String(50),
            nullable=False,
            server_default="portfolio",
        ),
    )

    # Drop existing FK constraints before altering nullability
    op.drop_constraint("sync_logs_user_id_fkey", "sync_logs", type_="foreignkey")
    op.drop_constraint("sync_logs_portfolio_id_fkey", "sync_logs", type_="foreignkey")

    # Make user_id and portfolio_id nullable
    op.alter_column("sync_logs", "user_id", nullable=True)
    op.alter_column("sync_logs", "portfolio_id", nullable=True)

    # Re-add FK constraints with nullable columns
    op.create_foreign_key(
        "sync_logs_user_id_fkey",
        "sync_logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "sync_logs_portfolio_id_fkey",
        "sync_logs",
        "portfolios",
        ["portfolio_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("sync_logs_user_id_fkey", "sync_logs", type_="foreignkey")
    op.drop_constraint("sync_logs_portfolio_id_fkey", "sync_logs", type_="foreignkey")

    op.alter_column("sync_logs", "user_id", nullable=False)
    op.alter_column("sync_logs", "portfolio_id", nullable=False)

    op.create_foreign_key(
        "sync_logs_user_id_fkey",
        "sync_logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "sync_logs_portfolio_id_fkey",
        "sync_logs",
        "portfolios",
        ["portfolio_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_column("sync_logs", "sync_type")
