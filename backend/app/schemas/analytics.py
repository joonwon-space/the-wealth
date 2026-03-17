"""Analytics API 응답 스키마."""

from pydantic import BaseModel


class MonthlyReturn(BaseModel):
    year: int
    month: int
    return_rate: float  # % (예: 2.5 = +2.5%)
