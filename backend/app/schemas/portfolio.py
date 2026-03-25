import re
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Korean ticker: exactly 6 alphanumeric chars (e.g. 005930, 0087F0 for ETFs)
# US ticker: 1–5 uppercase letters (e.g. AAPL, TSLA)
_TICKER_RE = re.compile(r"^[0-9A-Z]{6}$|^[A-Z]{1,5}$")


def validate_ticker(value: str) -> str:
    """Validate and normalise a stock ticker symbol."""
    value = value.strip().upper()
    if not _TICKER_RE.match(value):
        raise ValueError(
            "ticker must be a 6-char Korean code (e.g. 005930, 0087F0) "
            "or 1–5 uppercase letters (e.g. AAPL)"
        )
    return value


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    currency: str = "KRW"


class PortfolioUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    currency: Optional[str] = None
    target_value: Optional[int] = Field(None, ge=0)


class ReorderItem(BaseModel):
    id: int
    display_order: int


class ReorderRequest(BaseModel):
    items: list[ReorderItem] = Field(min_length=1)


class PortfolioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    currency: str
    display_order: int = 0
    created_at: datetime
    holdings_count: int = 0
    total_invested: Decimal = Decimal("0")
    kis_account_id: Optional[int] = None
    target_value: Optional[int] = None


class HoldingCreate(BaseModel):
    ticker: str
    name: str
    quantity: Decimal = Field(gt=0)
    avg_price: Decimal = Field(gt=0)
    market: Optional[str] = None  # e.g. "NAS", "NYS" for overseas; None for domestic

    @field_validator("ticker")
    @classmethod
    def ticker_format(cls, v: str) -> str:
        return validate_ticker(v)


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
    market: Optional[str] = None
    created_at: datetime


class TransactionCreate(BaseModel):
    ticker: str
    type: Literal["BUY", "SELL"]
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    traded_at: Optional[datetime] = None

    @field_validator("ticker")
    @classmethod
    def ticker_format(cls, v: str) -> str:
        return validate_ticker(v)


class TransactionMemoUpdate(BaseModel):
    memo: Optional[str] = Field(None, max_length=500)


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    ticker: str
    type: str
    quantity: Decimal
    price: Decimal
    traded_at: datetime
    memo: Optional[str] = None


class TransactionPage(BaseModel):
    """Cursor-based paginated response for transactions."""

    items: list[TransactionResponse]
    next_cursor: Optional[int] = None  # ID of the last item; None if no more pages
    has_more: bool
