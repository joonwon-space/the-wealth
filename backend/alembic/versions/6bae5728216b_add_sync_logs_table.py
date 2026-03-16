"""add_sync_logs_table

Revision ID: 6bae5728216b
Revises: d85c518e3bdb
Create Date: 2026-03-16 10:06:25.457448

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "6bae5728216b"
down_revision: Union[str, Sequence[str], None] = "d85c518e3bdb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sync_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.String(500), nullable=False, server_default=""),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_logs_id", "sync_logs", ["id"])
    op.create_index("ix_sync_logs_user_id", "sync_logs", ["user_id"])


def downgrade() -> None:
    op.drop_table("sync_logs")
