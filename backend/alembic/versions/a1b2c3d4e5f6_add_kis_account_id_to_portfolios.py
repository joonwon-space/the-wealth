"""add_kis_account_id_to_portfolios

Revision ID: a1b2c3d4e5f6
Revises: ec6205b4291f
Create Date: 2026-03-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "ec6205b4291f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "portfolios",
        sa.Column(
            "kis_account_id",
            sa.Integer(),
            sa.ForeignKey("kis_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_unique_constraint(
        "uq_portfolios_kis_account_id", "portfolios", ["kis_account_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_portfolios_kis_account_id", "portfolios", type_="unique")
    op.drop_column("portfolios", "kis_account_id")
