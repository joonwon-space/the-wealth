from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class HoldingWithPnL(BaseModel):
    id: int
    ticker: str
    name: str
    quantity: Decimal
    avg_price: Decimal
    current_price: Optional[Decimal]
    market_value: Optional[Decimal]
    pnl_amount: Optional[Decimal]
    pnl_rate: Optional[Decimal]

    class Config:
        from_attributes = True


class DashboardSummary(BaseModel):
    total_asset: Decimal
    total_invested: Decimal
    total_pnl_amount: Decimal
    total_pnl_rate: Decimal
    holdings: list[HoldingWithPnL]
    allocation: list[AllocationItem]


class AllocationItem(BaseModel):
    ticker: str
    name: str
    value: Decimal
    ratio: Decimal
