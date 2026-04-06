from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IndexSnapshot(Base):
    """주요 지수 일별/시간별 스냅샷. 벤치마크 비교에 사용.

    Supported index codes:
    - KOSPI200  (KIS TR_ID: FHKUP03500100)
    - SP500     (KIS TR_ID: FHKST03030100)
    """

    __tablename__ = "index_snapshots"
    __table_args__ = (
        UniqueConstraint("index_code", "timestamp", name="uq_index_snapshot_code_ts"),
        Index("ix_index_snapshot_code_ts", "index_code", "timestamp"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    index_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    change_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
