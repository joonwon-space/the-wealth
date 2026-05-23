"""add users.birth_year + users.simulation_params

Revision ID: p8q9r0s1t2u3
Revises: o7p8q9r0s1t2
Create Date: 2026-05-23 12:00:00.000000

연간 수익률 메뉴(은퇴 시뮬레이션)를 위한 사용자 프로필 확장.
  - `birth_year` : 나이 표시용. NULL 허용 (미입력 사용자 호환).
  - `simulation_params` : 시뮬레이션 폼 입력값 캐시 (JSONB). NULL 허용.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "p8q9r0s1t2u3"
down_revision: Union[str, None] = "o7p8q9r0s1t2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("birth_year", sa.SmallInteger(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("simulation_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "simulation_params")
    op.drop_column("users", "birth_year")
