"""배당 스냅샷 (KIS API로 수집하거나 수동 입력).

데이터 소스:
  - `kis_domestic`      : KIS 예탁원정보(배당일정) [국내주식-145], TR_ID HHKDB669102C0
  - `kis_overseas_ice`  : KIS 해외주식 ICE 권리조회, TR_ID HHDFS78330900
  - `kis_overseas_period`: KIS 해외주식 기간별권리조회, TR_ID CTRGT011R
  - `manual`            : 사용자 직접 입력
"""

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

DIVIDEND_KINDS = ("cash", "stock", "special", "interim")
DIVIDEND_SOURCES = (
    "kis_domestic",
    "kis_overseas_ice",
    "kis_overseas_period",
    "manual",
)


class Dividend(Base):
    __tablename__ = "dividends"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "market",
            "record_date",
            "kind",
            name="uq_dividends_ticker_market_record_kind",
        ),
        CheckConstraint(
            f"kind IN {DIVIDEND_KINDS}",
            name="ck_dividends_kind",
        ),
        CheckConstraint(
            f"source IN {DIVIDEND_SOURCES}",
            name="ck_dividends_source",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    market: Mapped[str] = mapped_column(String(8), nullable=False)
    # 배당락일 — 국내는 record_date 기준으로 계산될 수도 있음 (주로 record_date - 1 영업일).
    # null 이면 해당 시장 규칙에 따라 파생.
    ex_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KRW")
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="cash")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    # KIS 원본 응답 한 줄을 그대로 보존 — 필드 이름·형식이 달라도 후처리 가능.
    raw: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
