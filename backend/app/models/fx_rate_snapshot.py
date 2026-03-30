"""환율 일별 스냅샷 모델."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FxRateSnapshot(Base):
    """일별 환율 스냅샷. USD/KRW 등 통화쌍의 종가 환율을 저장한다."""

    __tablename__ = "fx_rate_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "currency_pair",
            "snapshot_date",
            name="uq_fx_rate_snapshot_pair_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    currency_pair: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True, comment="통화쌍 (예: USDKRW)"
    )
    rate: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
