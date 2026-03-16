"""add_kis_accounts_table

Revision ID: ec6205b4291f
Revises: 2f9ac6b822b2
Create Date: 2026-03-16 15:11:42.652875

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec6205b4291f'
down_revision: Union[str, Sequence[str], None] = '2f9ac6b822b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kis_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("account_no", sa.String(20), nullable=False),
        sa.Column("acnt_prdt_cd", sa.String(5), nullable=False, server_default="01"),
        sa.Column("app_key_enc", sa.String(512), nullable=False),
        sa.Column("app_secret_enc", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("kis_accounts")
