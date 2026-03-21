"""add display_order to portfolios

Revision ID: 444985fd4de7
Revises: 61cd677d984b
Create Date: 2026-03-21 21:15:43.505332

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '444985fd4de7'
down_revision: Union[str, Sequence[str], None] = '61cd677d984b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('portfolios', sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'))
    # 기존 데이터: created_at 순으로 user별 순서 부여
    op.execute("""
        UPDATE portfolios p
        SET display_order = sub.rn - 1
        FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at) AS rn
            FROM portfolios
        ) sub
        WHERE p.id = sub.id
    """)


def downgrade() -> None:
    op.drop_column('portfolios', 'display_order')
