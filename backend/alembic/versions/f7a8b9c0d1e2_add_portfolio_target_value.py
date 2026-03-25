"""add_portfolio_target_value

Revision ID: f7a8b9c0d1e2
Revises: cdf80f13c5f6
Create Date: 2026-03-25 16:50:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "cdf80f13c5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add target_value column to portfolios table."""
    op.add_column(
        "portfolios",
        sa.Column("target_value", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    """Remove target_value column from portfolios table."""
    op.drop_column("portfolios", "target_value")
