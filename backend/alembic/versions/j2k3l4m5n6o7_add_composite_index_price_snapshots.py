"""add composite index on price_snapshots (ticker, snapshot_date)

Revision ID: j2k3l4m5n6o7
Revises: i1j2k3l4m5n6
Create Date: 2026-04-02 08:45:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j2k3l4m5n6o7"
down_revision: Union[str, None] = "i1j2k3l4m5n6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_price_snapshot_ticker_date",
        "price_snapshots",
        ["ticker", "snapshot_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_price_snapshot_ticker_date", table_name="price_snapshots")
