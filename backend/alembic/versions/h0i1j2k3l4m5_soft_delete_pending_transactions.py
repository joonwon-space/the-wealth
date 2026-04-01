"""soft delete transactions created by unfilled pending orders

Revision ID: h0i1j2k3l4m5
Revises: g9h0i1j2k3l4
Create Date: 2026-04-01 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "h0i1j2k3l4m5"
down_revision: Union[str, None] = "g9h0i1j2k3l4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """order_source='kis'이고 해당 Order가 pending/cancelled/failed인 transaction을 soft delete."""
    op.execute(
        sa.text("""
            UPDATE transactions t
            SET deleted_at = NOW()
            FROM orders o
            WHERE t.order_no = o.order_no
              AND t.order_source = 'kis'
              AND t.deleted_at IS NULL
              AND o.status IN ('pending', 'cancelled', 'failed')
        """)
    )


def downgrade() -> None:
    """soft delete를 되돌린다 (이 마이그레이션으로 삭제된 것만 복원은 불가 — no-op)."""
    pass
