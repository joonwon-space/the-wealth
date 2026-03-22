"""merge display_order and transaction_memo heads

Revision ID: e6f7a8b9c0d1
Revises: 444985fd4de7, d5e6f7a8b9c0
Create Date: 2026-03-22 00:02:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: tuple[str, str] = ("444985fd4de7", "d5e6f7a8b9c0")
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
