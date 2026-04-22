"""redesign step 2 schema: target_allocation, strategy_tag, alert conditions, dividends, routine_logs

Revision ID: m5n6o7p8q9r0
Revises: l4m5n6o7p8q9
Create Date: 2026-04-22 11:30:00.000000

redesign-spec.md §1.3 의 신규 백엔드 요구를 한 번에 반영한다.

  1. portfolios.target_allocation  JSONB  NULL              (섹터별 목표 비중)
  2. users.strategy_tag            TEXT   DEFAULT 'mixed'   (long/short/mixed)
     users.long_short_ratio        SMALLINT DEFAULT 70      (혼합 시 장기 비중 %)
  3. alerts.condition              enum → varchar + CHECK   (above/below 에 pct_change/drawdown 추가)
  4. dividends                     new table                (KIS 배당 API 캐시)
  5. routine_logs                  new table                (리밸런싱·루틴 체크 로그)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m5n6o7p8q9r0"
down_revision: Union[str, None] = "l4m5n6o7p8q9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1) portfolios.target_allocation JSONB
    # ------------------------------------------------------------------
    op.add_column(
        "portfolios",
        sa.Column("target_allocation", postgresql.JSONB(), nullable=True),
    )

    # ------------------------------------------------------------------
    # 2) users.strategy_tag + long_short_ratio
    # ------------------------------------------------------------------
    strategy_enum = postgresql.ENUM(
        "long", "short", "mixed", name="strategy_tag", create_type=True
    )
    strategy_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column(
            "strategy_tag",
            sa.Enum("long", "short", "mixed", name="strategy_tag", create_type=False),
            nullable=False,
            server_default="mixed",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "long_short_ratio",
            sa.SmallInteger(),
            nullable=False,
            server_default="70",
        ),
    )

    # ------------------------------------------------------------------
    # 3) alerts.condition: enum → varchar + CHECK
    #    기존 데이터는 'above' / 'below' 뿐이므로 직접 캐스팅 가능.
    # ------------------------------------------------------------------
    # 일단 varchar 로 변환 (enum → text → varchar).
    op.alter_column(
        "alerts",
        "condition",
        existing_type=postgresql.ENUM("above", "below", name="alert_condition"),
        type_=sa.String(length=20),
        existing_nullable=False,
        postgresql_using="condition::text",
    )
    # 더 이상 쓰지 않는 enum 타입 제거.
    op.execute("DROP TYPE IF EXISTS alert_condition")
    # 확장된 조건 집합을 CHECK 로 강제.
    op.create_check_constraint(
        "ck_alerts_condition",
        "alerts",
        "condition IN ('above', 'below', 'pct_change', 'drawdown')",
    )

    # ------------------------------------------------------------------
    # 4) dividends
    # ------------------------------------------------------------------
    op.create_table(
        "dividends",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("market", sa.String(length=8), nullable=False),
        sa.Column("ex_date", sa.Date(), nullable=True),
        sa.Column("record_date", sa.Date(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "currency", sa.String(length=3), nullable=False, server_default="KRW"
        ),
        sa.Column(
            "kind", sa.String(length=16), nullable=False, server_default="cash"
        ),
        sa.Column(
            "source", sa.String(length=32), nullable=False, server_default="manual"
        ),
        sa.Column("raw", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ticker",
            "market",
            "record_date",
            "kind",
            name="uq_dividends_ticker_market_record_kind",
        ),
        sa.CheckConstraint(
            "kind IN ('cash', 'stock', 'special', 'interim')",
            name="ck_dividends_kind",
        ),
        sa.CheckConstraint(
            "source IN ('kis_domestic', 'kis_overseas_ice', 'kis_overseas_period', 'manual')",
            name="ck_dividends_source",
        ),
    )
    op.create_index("ix_dividends_id", "dividends", ["id"], unique=False)
    op.create_index("ix_dividends_ticker", "dividends", ["ticker"], unique=False)
    op.create_index("ix_dividends_ex_date", "dividends", ["ex_date"], unique=False)

    # ------------------------------------------------------------------
    # 5) routine_logs
    # ------------------------------------------------------------------
    op.create_table(
        "routine_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=True),
        sa.Column("routine_kind", sa.String(length=32), nullable=False),
        sa.Column("period_key", sa.String(length=16), nullable=False),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "portfolio_id",
            "routine_kind",
            "period_key",
            name="uq_routine_logs_user_portfolio_kind_period",
        ),
        sa.CheckConstraint(
            "routine_kind IN ('rebalance_monthly', 'rebalance_quarterly', 'dividend_review')",
            name="ck_routine_logs_kind",
        ),
    )
    op.create_index("ix_routine_logs_id", "routine_logs", ["id"], unique=False)
    op.create_index("ix_routine_logs_user_id", "routine_logs", ["user_id"], unique=False)
    op.create_index(
        "ix_routine_logs_portfolio_id",
        "routine_logs",
        ["portfolio_id"],
        unique=False,
    )


def downgrade() -> None:
    # 5) routine_logs
    op.drop_index("ix_routine_logs_portfolio_id", table_name="routine_logs")
    op.drop_index("ix_routine_logs_user_id", table_name="routine_logs")
    op.drop_index("ix_routine_logs_id", table_name="routine_logs")
    op.drop_table("routine_logs")

    # 4) dividends
    op.drop_index("ix_dividends_ex_date", table_name="dividends")
    op.drop_index("ix_dividends_ticker", table_name="dividends")
    op.drop_index("ix_dividends_id", table_name="dividends")
    op.drop_table("dividends")

    # 3) alerts.condition: varchar → enum('above','below')
    op.drop_constraint("ck_alerts_condition", "alerts", type_="check")
    # 다운그레이드 전에 확장값이 들어 있으면 제거하거나 'below' 로 강등.
    # 데이터 손실을 막기 위해 `pct_change`/`drawdown` 은 'below' 로 수렴시킨다.
    op.execute(
        "UPDATE alerts SET condition = 'below' "
        "WHERE condition IN ('pct_change', 'drawdown')"
    )
    alert_enum = postgresql.ENUM(
        "above", "below", name="alert_condition", create_type=True
    )
    alert_enum.create(op.get_bind(), checkfirst=True)
    op.alter_column(
        "alerts",
        "condition",
        existing_type=sa.String(length=20),
        type_=sa.Enum("above", "below", name="alert_condition", create_type=False),
        existing_nullable=False,
        postgresql_using="condition::alert_condition",
    )

    # 2) users
    op.drop_column("users", "long_short_ratio")
    op.drop_column("users", "strategy_tag")
    op.execute("DROP TYPE IF EXISTS strategy_tag")

    # 1) portfolios
    op.drop_column("portfolios", "target_allocation")
