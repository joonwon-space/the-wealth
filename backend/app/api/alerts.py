"""목표가 알림 API."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.alert import Alert
from app.models.user import User

router = APIRouter(prefix="/alerts", tags=["alerts"])
logger = get_logger(__name__)

_ALERT_COOLDOWN_SECONDS = 3600  # 1 hour between repeated triggers for same alert


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


class AlertPatch(BaseModel):
    is_active: Optional[bool] = None
    threshold: Optional[Decimal] = None

    @field_validator("threshold")
    @classmethod
    def threshold_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("threshold must be positive")
        return v


class AlertOut(BaseModel):
    id: int
    ticker: str
    name: str
    condition: str
    threshold: Decimal
    is_active: bool
    last_triggered_at: Optional[datetime] = None

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


@router.patch("/{alert_id}", response_model=AlertOut)
async def patch_alert(
    alert_id: int,
    body: AlertPatch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Alert:
    """알림 활성화/비활성화 또는 임계값 변경."""
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")

    if body.is_active is not None:
        alert.is_active = body.is_active
    if body.threshold is not None:
        alert.threshold = body.threshold

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


def _is_cooldown_active(alert: Alert, now: datetime) -> bool:
    """1시간 쿨다운 중이면 True 반환."""
    if alert.last_triggered_at is None:
        return False
    last = alert.last_triggered_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (now - last).total_seconds() < _ALERT_COOLDOWN_SECONDS


def check_and_dedup_alerts(
    alerts: list[Alert],
    current_prices: dict[str, Optional[Decimal]],
) -> list[dict]:
    """현재가와 알림 조건 비교.

    - 1시간 쿨다운 중인 알림은 건너뜀.
    - 트리거된 알림은 last_triggered_at, is_active(False)를 in-place 업데이트.
      (호출자가 DB commit 책임)
    - 트리거된 알림 목록 반환.
    """
    now = datetime.now(timezone.utc)
    triggered: list[dict] = []
    for alert in alerts:
        if not alert.is_active:
            continue
        if _is_cooldown_active(alert, now):
            continue
        price = current_prices.get(alert.ticker)
        if price is None:
            continue
        threshold = Decimal(str(alert.threshold))
        hit = (alert.condition == "above" and price >= threshold) or (
            alert.condition == "below" and price <= threshold
        )
        if not hit:
            continue

        # Mark alert as triggered and auto-deactivate
        alert.last_triggered_at = now
        alert.is_active = False

        triggered.append({
            "id": alert.id,
            "ticker": alert.ticker,
            "name": alert.name,
            "condition": alert.condition,
            "threshold": float(threshold),
            "current_price": float(price),
        })
        logger.info(
            "Alert triggered: id=%s ticker=%s condition=%s threshold=%s price=%s",
            alert.id,
            alert.ticker,
            alert.condition,
            threshold,
            price,
        )
    return triggered
