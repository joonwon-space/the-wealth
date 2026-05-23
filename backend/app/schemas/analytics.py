"""Analytics API 응답 스키마."""

from typing import Optional

from pydantic import BaseModel, Field


class MonthlyReturn(BaseModel):
    year: int
    month: int
    return_rate: float  # % (예: 2.5 = +2.5%)


class AnnualReturn(BaseModel):
    """연도별 자본흐름 + 평가액 + IRR (KRW 기준)."""

    year: int
    age: Optional[int] = None  # users.birth_year 입력 시에만 채움
    bop_value_krw: float = 0.0       # 전년 말 평가액 (첫 해는 0)
    contributions_krw: float = 0.0   # 해당 연도 순 매입 (BUY - SELL)
    dividends_krw: float = 0.0       # 해당 연도 수령 배당 합계
    eop_value_krw: float = 0.0       # 연말 평가액
    pnl_amount_krw: float = 0.0      # eop - bop - contributions + dividends
    irr_year: Optional[float] = None        # 해당 연도 1년 IRR (소수, 0.07 = 7%)
    irr_cumulative: Optional[float] = None  # 최초 매수일 ~ 해당 연말 누적 IRR


class SimulationInput(BaseModel):
    """은퇴 시뮬레이션 입력값."""

    current_value_krw: float = Field(ge=0)
    current_age: int = Field(ge=0, le=120)
    retirement_age: int = Field(ge=0, le=120)
    end_age: int = Field(ge=0, le=120)
    annual_contribution_krw: float = Field(ge=0)
    annual_withdrawal_krw: float = Field(ge=0)
    expected_return_rate: float = Field(ge=-0.5, le=1.0)  # -50% ~ +100%


class SimulationPoint(BaseModel):
    age: int
    year: int
    flow_krw: float           # +적립 / -인출
    return_amount_krw: float  # bop * rate
    eop_value_krw: float


class PortfolioHistoryPoint(BaseModel):
    date: str  # ISO date string "YYYY-MM-DD"
    value: float  # 포트폴리오 총 평가금액 (원)


class SectorAllocation(BaseModel):
    sector: str   # 섹터명 (예: "IT", "금융", "헬스케어")
    value: float  # 해당 섹터 평가금액 (원)
    weight: float  # 비중 % (예: 35.2 = 35.2%)


class SmaPoint(BaseModel):
    date: str  # ISO date string "YYYY-MM-DD"
    sma: float  # 단순 이동평균 값


class BenchmarkPoint(BaseModel):
    date: str  # ISO date string "YYYY-MM-DD"
    close_price: float  # 지수 종가


class FxGainLossItem(BaseModel):
    ticker: str
    name: str
    quantity: float
    avg_price_usd: float
    current_price_usd: float
    stock_pnl_usd: float
    fx_rate_at_buy: float
    fx_rate_current: float
    fx_gain_krw: float
    stock_gain_krw: float
    total_pnl_krw: float
