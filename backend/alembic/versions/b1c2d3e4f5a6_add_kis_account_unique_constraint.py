"""add_kis_account_unique_constraint

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-03-16
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_kis_account_per_user", "kis_accounts",
        ["user_id", "account_no", "acnt_prdt_cd"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_kis_account_per_user", "kis_accounts", type_="unique")
