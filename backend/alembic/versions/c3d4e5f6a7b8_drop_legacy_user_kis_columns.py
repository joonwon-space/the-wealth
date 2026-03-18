"""drop legacy KIS columns from users table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-18 18:30:00.000000

Removes legacy KIS credential columns that have been superseded by the
kis_accounts table. The columns kis_app_key_enc, kis_app_secret_enc,
kis_account_no, and kis_acnt_prdt_cd are no longer referenced in code.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "kis_app_key_enc")
    op.drop_column("users", "kis_app_secret_enc")
    op.drop_column("users", "kis_account_no")
    op.drop_column("users", "kis_acnt_prdt_cd")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("kis_acnt_prdt_cd", sa.String(length=5), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("kis_account_no", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("kis_app_secret_enc", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("kis_app_key_enc", sa.String(length=512), nullable=True),
    )
