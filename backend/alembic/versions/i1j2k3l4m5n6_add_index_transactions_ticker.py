"""add index on transactions.ticker

Revision ID: i1j2k3l4m5n6
Revises: h0i1j2k3l4m5
Create Date: 2026-04-02 08:40:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i1j2k3l4m5n6"
down_revision: Union[str, None] = "h0i1j2k3l4m5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        op.f("ix_transactions_ticker"),
        "transactions",
        ["ticker"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_ticker"), table_name="transactions")
