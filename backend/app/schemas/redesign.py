"""Schemas backing the Phase 3 / Step 3 APIs (redesign-spec.md §1.4).

목표 비중, 리밸런싱 제안, 다가오는 배당, 벤치마크 델타, 스트림, 오늘 할 것 등.
기존 schemas/ 파일을 오염시키지 않도록 별도 파일로 분리.
"""

from __future__ import annotations

from datetime import date as date_type, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# -----------------------------------------------------------------
# Target allocation / rebalance
# -----------------------------------------------------------------
class TargetAllocationUpdate(BaseModel):
    """섹터별 목표 비중.

    값은 0..1 범위 실수. 합이 반드시 1.0 일 필요는 없지만 1.0 ± 0.01 을 권장.
    """

    target_allocation: dict[str, float] = Field(
        ..., description="섹터명 → 목표 비중 (0..1)"
    )

    @field_validator("target_allocation")
    @classmethod
    def _validate_fractions(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("최소 하나의 섹터 목표 비중을 지정해야 합니다.")
        for sector, ratio in value.items():
            if not 0 <= ratio <= 1:
                raise ValueError(
                    f"{sector} 비중이 0..1 범위를 벗어났습니다: {ratio}"
                )
        return value


class TargetAllocationResponse(BaseModel):
    portfolio_id: int
    target_allocation: Optional[dict[str, float]] = None


class RebalanceSuggestionRow(BaseModel):
    sector: str
    current_pct: float = Field(description="현재 비중 0..1")
    target_pct: float = Field(description="목표 비중 0..1")
    diff_pct: float = Field(description="current - target (양수면 초과)")
    delta_krw: float = Field(description="목표까지 이동할 원화 금액 (+ 매도 / - 매수)")
    suggested_action: Literal["BUY", "SELL", "HOLD"]
    candidates: list["RebalanceCandidate"] = []


class RebalanceCandidate(BaseModel):
    ticker: str
    name: str
    weight_in_sector: float
    suggested_qty: float = Field(description="제안 수량 (부호 없음)")
    suggested_action: Literal["BUY", "SELL"]


class RebalanceSuggestionResponse(BaseModel):
    portfolio_id: int
    total_value_krw: float
    rows: list[RebalanceSuggestionRow]


RebalanceSuggestionRow.model_rebuild()


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
# Stream
# -----------------------------------------------------------------
StreamKind = Literal["alert", "fill", "dividend", "rebalance", "routine"]


class StreamItem(BaseModel):
    id: str = Field(
        description="타입 내 고유 식별자, 예: alert:42 / fill:1203 / dividend:5 / rebalance:p1-202604 / routine:user-123-202604"
    )
    kind: StreamKind
    ts: datetime
    title: str
    sub: Optional[str] = None
    payload: dict = Field(
        default_factory=dict,
        description="프론트에서 카드를 렌더할 때 쓰는 보조 데이터 (ticker, portfolio_id 등)",
    )


class StreamResponse(BaseModel):
    items: list[StreamItem]
    next_cursor: Optional[str] = None


# -----------------------------------------------------------------
# Tasks
# -----------------------------------------------------------------
TaskKind = Literal["rebalance", "dividend", "alert", "routine", "goal"]


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


# -----------------------------------------------------------------
# User strategy
# -----------------------------------------------------------------
class StrategyUpdate(BaseModel):
    strategy_tag: Literal["long", "short", "mixed"]
    long_short_ratio: int = Field(ge=0, le=100, default=70)
