"""add index_snapshots table

Revision ID: l4m5n6o7p8q9
Revises: k3l4m5n6o7p8
Create Date: 2026-04-06 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "l4m5n6o7p8q9"
down_revision: Union[str, None] = "k3l4m5n6o7p8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "index_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("index_code", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("change_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("index_code", "timestamp", name="uq_index_snapshot_code_ts"),
    )
    op.create_index("ix_index_snapshots_id", "index_snapshots", ["id"], unique=False)
    op.create_index(
        "ix_index_snapshots_index_code",
        "index_snapshots",
        ["index_code"],
        unique=False,
    )
    op.create_index(
        "ix_index_snapshot_code_ts",
        "index_snapshots",
        ["index_code", "timestamp"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_index_snapshot_code_ts", table_name="index_snapshots")
    op.drop_index("ix_index_snapshots_index_code", table_name="index_snapshots")
    op.drop_index("ix_index_snapshots_id", table_name="index_snapshots")
    op.drop_table("index_snapshots")
