from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PortfolioCreate(BaseModel):
    name: str
    currency: str = "KRW"


class PortfolioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    currency: str
    created_at: datetime
    holdings_count: int = 0
    total_invested: Decimal = Decimal("0")


class HoldingCreate(BaseModel):
    ticker: str
    name: str
    quantity: Decimal
    avg_price: Decimal


class HoldingUpdate(BaseModel):
    quantity: Optional[Decimal] = None
    avg_price: Optional[Decimal] = None


class HoldingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    ticker: str
    name: str
    quantity: Decimal
    avg_price: Decimal
    created_at: datetime
