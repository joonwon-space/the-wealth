"""merge soft delete and market column heads

Revision ID: e4f5a6b7c8d9
Revises: d4e5f6a7b8c9, b3c4d5e6f7a8
Create Date: 2026-03-18 19:30:00.000000

"""
from typing import Sequence, Union

revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = ("d4e5f6a7b8c9", "b3c4d5e6f7a8")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
