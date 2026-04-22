"""월/분기 리밸런싱 체크 로그.

사용자가 정해진 주기(월간·분기)마다 리밸런싱 체크를 완료했는지 추적한다.
Stream 피드의 "루틴" 카드가 이 테이블을 기준으로 렌더링된다.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ROUTINE_KINDS = ("rebalance_monthly", "rebalance_quarterly", "dividend_review")


class RoutineLog(Base):
    __tablename__ = "routine_logs"
    __table_args__ = (
        # 한 사용자 기준 한 포트폴리오·루틴·기간(YYYY-MM or YYYY-Qn)에 대해 1건.
        UniqueConstraint(
            "user_id",
            "portfolio_id",
            "routine_kind",
            "period_key",
            name="uq_routine_logs_user_portfolio_kind_period",
        ),
        CheckConstraint(
            f"routine_kind IN {ROUTINE_KINDS}",
            name="ck_routine_logs_kind",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    portfolio_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=True, index=True
    )
    routine_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    # 'YYYY-MM' (monthly) 또는 'YYYY-Qn' (quarterly) 등 루틴별 기간 식별자.
    period_key: Mapped[str] = mapped_column(String(16), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # 체크 당시 스냅샷(현재 섹터 비중 vs 목표, 결정사항 메모 등).
    snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
