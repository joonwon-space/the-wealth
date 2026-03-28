"""Pydantic schemas for the orders API."""

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class OrderRequest(BaseModel):
    """주문 요청 스키마."""

    ticker: str = Field(..., min_length=1, max_length=20)
    name: Optional[str] = Field(None, max_length=100)
    order_type: Literal["BUY", "SELL"]
    order_class: Literal["limit", "market"] = "limit"
    quantity: int = Field(..., gt=0)
    price: Optional[Decimal] = Field(None, ge=0)
    exchange_code: Optional[str] = Field(None, max_length=10)  # 해외 거래소 코드
    memo: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def validate_limit_price(self) -> "OrderRequest":
        if self.order_class == "limit" and (self.price is None or self.price <= 0):
            raise ValueError("지정가 주문에는 0보다 큰 가격을 입력해야 합니다")
        return self


class OrderResult(BaseModel):
    """주문 결과 스키마."""

    id: int
    order_no: Optional[str] = None
    ticker: str
    name: Optional[str] = None
    order_type: str
    order_class: str
    quantity: Decimal
    price: Optional[Decimal] = None
    status: str
    filled_quantity: Optional[Decimal] = None
    filled_price: Optional[Decimal] = None
    memo: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderableInfoResponse(BaseModel):
    """주문 가능 수량/금액 조회 응답."""

    orderable_quantity: Decimal
    orderable_amount: Decimal
    current_price: Optional[Decimal] = None
    currency: str = "KRW"


class CashBalanceResponse(BaseModel):
    """예수금 및 총 평가금액 응답."""

    total_cash: Decimal
    available_cash: Decimal
    total_evaluation: Decimal
    total_profit_loss: Decimal
    profit_loss_rate: Decimal
    currency: str = "KRW"
    foreign_cash: Optional[Decimal] = None
    usd_krw_rate: Optional[Decimal] = None


class PendingOrderResponse(BaseModel):
    """미체결 주문 응답."""

    order_no: str
    ticker: str
    name: str
    order_type: str
    order_class: str
    quantity: Decimal
    price: Decimal
    filled_quantity: Decimal
    remaining_quantity: Decimal
    order_time: str
