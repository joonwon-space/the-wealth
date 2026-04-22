from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# 허용되는 알림 조건. 마이그레이션의 CHECK 제약과 반드시 일치해야 함.
#  - above       : 현재가 >= threshold
#  - below       : 현재가 <= threshold
#  - pct_change  : 오늘 변동율(|day_change_pct|)이 threshold(%) 이상
#  - drawdown    : 평균 매수가 대비 낙폭이 threshold(%) 이상
ALERT_CONDITIONS = ("above", "below", "pct_change", "drawdown")


class Alert(Base):
    """가격·등락·낙폭 알림 설정."""

    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(
            "condition IN ('above', 'below', 'pct_change', 'drawdown')",
            name="ck_alerts_condition",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    condition: Mapped[str] = mapped_column(String(20), nullable=False)
    threshold: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Tracks last trigger time for dedup cooldown (1h) and auto-deactivation logic
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
