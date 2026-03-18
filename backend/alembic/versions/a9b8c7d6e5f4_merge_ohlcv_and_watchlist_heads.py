"""merge ohlcv and watchlist heads

Revision ID: a9b8c7d6e5f4
Revises: e1f2a3b4c5d6, f1a2b3c4d5e6
Create Date: 2026-03-18 16:00:00.000000

"""
from typing import Sequence, Union

revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, Sequence[str], None] = ("e1f2a3b4c5d6", "f1a2b3c4d5e6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
