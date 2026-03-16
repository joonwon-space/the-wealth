from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class PortfolioCreate(BaseModel):
    name: str
    currency: str = "KRW"


class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    name: str
    currency: str
    created_at: datetime

    class Config:
        from_attributes = True


class HoldingCreate(BaseModel):
    ticker: str
    name: str
    quantity: Decimal
    avg_price: Decimal


class HoldingUpdate(BaseModel):
    quantity: Optional[Decimal] = None
    avg_price: Optional[Decimal] = None


class HoldingResponse(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    name: str
    quantity: Decimal
    avg_price: Decimal
    created_at: datetime

    class Config:
        from_attributes = True
