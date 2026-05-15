from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class HoldingWithPnL(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    name: str
    portfolio_name: Optional[str] = None
    quantity: Decimal
    avg_price: Decimal
    current_price: Optional[Decimal]
    market_value: Optional[Decimal]
    market_value_krw: Optional[Decimal]  # 해외주식의 원화 환산 시가총액 (allocation/합산용)
    pnl_amount: Optional[Decimal]
    pnl_rate: Optional[Decimal]
    day_change_rate: Optional[Decimal]  # 전일 대비율 (%, e.g. 1.25 means +1.25%)
    w52_high: Optional[Decimal]
    w52_low: Optional[Decimal]
    currency: str = "KRW"  # "KRW" for domestic, "USD" for overseas


class AllocationItem(BaseModel):
    ticker: str
    name: str
    value: Decimal
    ratio: Decimal


class TriggeredAlert(BaseModel):
    id: int
    ticker: str
    name: str
    condition: str
    threshold: float
    current_price: float


class DashboardSummaryResponse(BaseModel):
    """Dashboard summary API response model — used as response_model for openapi-typescript generation."""

    total_asset: Decimal
    total_invested: Decimal
    total_pnl_amount: Decimal
    total_pnl_rate: Decimal
    total_day_change_rate: Optional[Decimal]
    day_change_pct: Optional[Decimal]
    day_change_amount: Optional[Decimal]
    holdings: list["HoldingWithPnL"]
    allocation: list["AllocationItem"]
    triggered_alerts: list["TriggeredAlert"] = []
    usd_krw_rate: Optional[Decimal] = None
    kis_status: str = "ok"
    total_cash: Optional[Decimal] = None
    total_assets: Optional[Decimal] = None


class DashboardSummary(BaseModel):
    total_asset: Decimal
    total_invested: Decimal
    total_pnl_amount: Decimal
    total_pnl_rate: Decimal
    total_day_change_rate: Optional[Decimal]  # 포트폴리오 전일 대비 가중 평균 변동률 (KIS 실시간)
    day_change_pct: Optional[Decimal]  # 전일 대비 변동률 % (price_snapshots 기반)
    day_change_amount: Optional[Decimal]  # 전일 대비 변동 금액 (price_snapshots 기반)
    holdings: list[HoldingWithPnL]
    allocation: list[AllocationItem]
    triggered_alerts: list[TriggeredAlert] = []
    usd_krw_rate: Optional[Decimal] = None  # 해외주식 환산에 사용된 USD/KRW 환율
    kis_status: str = "ok"  # "ok" | "degraded" — KIS 가격 조회 실패 시 "degraded"
    total_cash: Optional[Decimal] = None  # 예수금 합계 (KIS 연결 포트폴리오에서만)
    total_assets: Optional[Decimal] = None  # 총 자산 = total_asset + total_cash


class CashSummaryAccount(BaseModel):
    """사용자의 단일 KIS 계좌에 대한 예수금/평가 정보."""

    kis_account_id: int
    label: str
    total_cash: Optional[Decimal] = None  # KRW 통합 (국내 + 해외 USD 환산)
    available_cash: Optional[Decimal] = None
    total_evaluation: Optional[Decimal] = None  # 종목 평가금액 (cash 미포함)
    total_profit_loss: Optional[Decimal] = None
    foreign_cash: Optional[Decimal] = None  # USD 외화예수금 원본
    usd_krw_rate: Optional[Decimal] = None
    error: Optional[str] = None  # 호출 실패 시 사유


class CashSummaryResponse(BaseModel):
    """사용자의 모든 KIS 계좌 예수금 합산. /dashboard/cash-summary 응답."""

    total_cash: Decimal  # 모든 KIS 계좌 예수금 합계 (KRW)
    available_cash: Decimal
    total_evaluation: Decimal  # 모든 계좌 종목 평가 합계
    total_profit_loss: Decimal
    kis_connected: bool  # KIS 계좌가 하나라도 연결되어 있는지
    accounts: list[CashSummaryAccount] = []
    has_errors: bool = False  # 부분 실패 시 true
