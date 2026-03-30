"""add fx_rate_snapshots table

Revision ID: a1b2c3d4e5f6
Revises: 3f3590b35dcf
Create Date: 2026-03-30 21:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "3f3590b35dcf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fx_rate_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "currency_pair",
            sa.String(length=10),
            nullable=False,
            comment="통화쌍 (예: USDKRW)",
        ),
        sa.Column("rate", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "currency_pair",
            "snapshot_date",
            name="uq_fx_rate_snapshot_pair_date",
        ),
    )
    op.create_index(
        op.f("ix_fx_rate_snapshots_currency_pair"),
        "fx_rate_snapshots",
        ["currency_pair"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fx_rate_snapshots_id"),
        "fx_rate_snapshots",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_fx_rate_snapshots_id"),
        table_name="fx_rate_snapshots",
    )
    op.drop_index(
        op.f("ix_fx_rate_snapshots_currency_pair"),
        table_name="fx_rate_snapshots",
    )
    op.drop_table("fx_rate_snapshots")
