"""add tags column to transactions

Revision ID: g9h0i1j2k3l4
Revises: f8a9b0c1d2e3
Create Date: 2026-03-30 21:45:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "g9h0i1j2k3l4"
down_revision: Union[str, None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
            server_default=None,
        ),
    )


def downgrade() -> None:
    op.drop_column("transactions", "tags")
