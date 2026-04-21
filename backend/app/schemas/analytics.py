"""Analytics API 응답 스키마."""

from pydantic import BaseModel


class MonthlyReturn(BaseModel):
    year: int
    month: int
    return_rate: float  # % (예: 2.5 = +2.5%)


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
