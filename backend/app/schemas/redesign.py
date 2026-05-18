"""Schemas backing the Phase 3 / Step 3 APIs (redesign-spec.md §1.4).

다가오는 배당, 벤치마크 델타, 오늘 할 것 등.

NOTE: TargetAllocation/Rebalance/Stream/StrategyUpdate 스키마들은
포트폴리오 상세 리밸런싱 섹션 / /dashboard/rebalance / /dashboard/stream
페이지 제거(2026-05-18)와 함께 dead 가 되어 정리됨.
"""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# -----------------------------------------------------------------
# Dividends
# -----------------------------------------------------------------
class UpcomingDividend(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    market: str
    name: Optional[str] = None
    quantity: Optional[Decimal] = Field(
        default=None, description="해당 종목 보유 수량. 비보유는 null."
    )
    ex_date: Optional[date_type] = None
    record_date: date_type
    payment_date: Optional[date_type] = None
    amount: Decimal
    currency: str
    kind: str
    source: str
    estimated_payout: Optional[Decimal] = Field(
        default=None,
        description="quantity × amount (해당 currency 기준).",
    )


# -----------------------------------------------------------------
# Benchmark delta
# -----------------------------------------------------------------
class BenchmarkDelta(BaseModel):
    index_code: str
    period: str = Field(description="e.g. 1M, 3M, 6M, 1Y, ALL")
    mine_pct: float
    benchmark_pct: float
    delta_pct_points: float


# -----------------------------------------------------------------
# Tasks
# -----------------------------------------------------------------
TaskKind = Literal["dividend", "alert", "routine", "goal"]


class HomeTask(BaseModel):
    id: str
    kind: TaskKind
    title: str
    sub: Optional[str] = None
    accent: Optional[str] = Field(
        default=None,
        description="컬러 토큰 이름 혹은 var(--...) 문자열",
    )
    priority: int = Field(default=50, description="0..100, 클수록 위에 노출")


class TodayTasksResponse(BaseModel):
    count: int
    tasks: list[HomeTask]
