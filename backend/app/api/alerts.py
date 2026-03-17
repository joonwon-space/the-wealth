"""목표가 알림 API."""

import logging
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.alert import Alert
from app.models.user import User

router = APIRouter(prefix="/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)


class AlertCreate(BaseModel):
    ticker: str
    name: str = ""
    condition: Literal["above", "below"]
    threshold: Decimal

    @field_validator("ticker")
    @classmethod
    def ticker_nonempty(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("ticker must not be empty")
        return v

    @field_validator("threshold")
    @classmethod
    def threshold_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("threshold must be positive")
        return v


class AlertOut(BaseModel):
    id: int
    ticker: str
    name: str
    condition: str
    threshold: Decimal
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Alert]:
    result = await db.execute(
        select(Alert)
        .where(Alert.user_id == current_user.id)
        .order_by(Alert.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=AlertOut, status_code=201)
async def create_alert(
    body: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Alert:
    alert = Alert(
        user_id=current_user.id,
        ticker=body.ticker,
        name=body.name,
        condition=body.condition,
        threshold=body.threshold,
        is_active=True,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
    await db.delete(alert)
    await db.commit()


def check_triggered_alerts(
    alerts: list[Alert],
    current_prices: dict[str, Optional[Decimal]],
) -> list[dict]:
    """현재가와 알림 조건 비교. 트리거된 알림 목록 반환."""
    triggered: list[dict] = []
    for alert in alerts:
        if not alert.is_active:
            continue
        price = current_prices.get(alert.ticker)
        if price is None:
            continue
        threshold = Decimal(str(alert.threshold))
        hit = (alert.condition == "above" and price >= threshold) or (
            alert.condition == "below" and price <= threshold
        )
        if hit:
            triggered.append({
                "id": alert.id,
                "ticker": alert.ticker,
                "name": alert.name,
                "condition": alert.condition,
                "threshold": float(threshold),
                "current_price": float(price),
            })
    return triggered
