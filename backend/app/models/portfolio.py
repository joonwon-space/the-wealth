from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.holding import Holding
    from app.models.order import Order
    from app.models.transaction import Transaction
    from app.models.user import User


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="KRW", nullable=False)
    kis_account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("kis_accounts.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_value: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    # 섹터별 목표 비중. 예: {"IT": 0.30, "소재": 0.20, "금융": 0.20, "헬스케어": 0.30}
    # 값의 합이 1.0 이 아닐 수 있음 — 애플리케이션에서 검증.
    target_allocation: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="portfolios")
    holdings: Mapped[List["Holding"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    orders: Mapped[List["Order"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
