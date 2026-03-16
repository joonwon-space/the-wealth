"""add_kis_account_fields_to_users

Revision ID: 2f9ac6b822b2
Revises: 6bae5728216b
Create Date: 2026-03-16 10:27:51.560315

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f9ac6b822b2"
down_revision: Union[str, Sequence[str], None] = "6bae5728216b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("kis_account_no", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("kis_acnt_prdt_cd", sa.String(5), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "kis_acnt_prdt_cd")
    op.drop_column("users", "kis_account_no")
