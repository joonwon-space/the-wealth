from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PriceSnapshot(Base):
    """일별 OHLCV 스냅샷. 전일 대비 계산 및 가격 히스토리에 사용."""

    __tablename__ = "price_snapshots"
    __table_args__ = (
        UniqueConstraint("ticker", "snapshot_date", name="uq_price_snapshot_ticker_date"),
        Index("ix_price_snapshot_ticker_date", "ticker", "snapshot_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    high: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    low: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    close: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
