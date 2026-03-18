"""add ohlcv columns to price_snapshots

Revision ID: e1f2a3b4c5d6
Revises: d8721aa82592
Create Date: 2026-03-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd8721aa82592'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add open, high, low, volume columns to price_snapshots."""
    op.add_column('price_snapshots', sa.Column('open', sa.Numeric(precision=18, scale=4), nullable=True))
    op.add_column('price_snapshots', sa.Column('high', sa.Numeric(precision=18, scale=4), nullable=True))
    op.add_column('price_snapshots', sa.Column('low', sa.Numeric(precision=18, scale=4), nullable=True))
    op.add_column('price_snapshots', sa.Column('volume', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    """Remove open, high, low, volume columns from price_snapshots."""
    op.drop_column('price_snapshots', 'volume')
    op.drop_column('price_snapshots', 'low')
    op.drop_column('price_snapshots', 'high')
    op.drop_column('price_snapshots', 'open')
