from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class HoldingWithPnL(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    name: str
    quantity: Decimal
    avg_price: Decimal
    current_price: Optional[Decimal]
    market_value: Optional[Decimal]
    pnl_amount: Optional[Decimal]
    pnl_rate: Optional[Decimal]


class AllocationItem(BaseModel):
    ticker: str
    name: str
    value: Decimal
    ratio: Decimal


class DashboardSummary(BaseModel):
    total_asset: Decimal
    total_invested: Decimal
    total_pnl_amount: Decimal
    total_pnl_rate: Decimal
    holdings: list[HoldingWithPnL]
    allocation: list[AllocationItem]
