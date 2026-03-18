"""add composite indexes for performance

Revision ID: b2c3d4e5f6a7
Revises: a9b8c7d6e5f4
Create Date: 2026-03-18 18:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # transactions: composite index on (portfolio_id, traded_at DESC)
    op.create_index(
        "ix_transactions_portfolio_traded_at",
        "transactions",
        ["portfolio_id", sa.text("traded_at DESC")],
        unique=False,
    )

    # price_snapshots: composite index on (ticker, snapshot_date DESC)
    op.create_index(
        "ix_price_snapshots_ticker_date",
        "price_snapshots",
        ["ticker", sa.text("snapshot_date DESC")],
        unique=False,
    )

    # sync_logs: composite index on (user_id, synced_at DESC)
    op.create_index(
        "ix_sync_logs_user_synced_at",
        "sync_logs",
        ["user_id", sa.text("synced_at DESC")],
        unique=False,
    )

    # alerts: partial index on (user_id) WHERE is_active = true
    op.create_index(
        "ix_alerts_user_active",
        "alerts",
        ["user_id"],
        unique=False,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("ix_alerts_user_active", table_name="alerts")
    op.drop_index("ix_sync_logs_user_synced_at", table_name="sync_logs")
    op.drop_index("ix_price_snapshots_ticker_date", table_name="price_snapshots")
    op.drop_index("ix_transactions_portfolio_traded_at", table_name="transactions")
