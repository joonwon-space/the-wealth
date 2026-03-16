"""add_performance_indexes

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-03-16
"""

from typing import Sequence, Union

from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_holdings_ticker_portfolio", "holdings", ["ticker", "portfolio_id"])
    op.create_index("ix_transactions_portfolio_traded", "transactions", ["portfolio_id", "traded_at"])
    op.create_index("ix_sync_logs_user_synced", "sync_logs", ["user_id", "synced_at"])


def downgrade() -> None:
    op.drop_index("ix_sync_logs_user_synced", "sync_logs")
    op.drop_index("ix_transactions_portfolio_traded", "transactions")
    op.drop_index("ix_holdings_ticker_portfolio", "holdings")
