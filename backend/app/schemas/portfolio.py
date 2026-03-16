from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
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


class TransactionCreate(BaseModel):
    ticker: str
    type: str  # BUY | SELL
    quantity: Decimal
    price: Decimal
    traded_at: Optional[datetime] = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    ticker: str
    type: str
    quantity: Decimal
    price: Decimal
    traded_at: datetime
