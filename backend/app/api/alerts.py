"""목표가 알림 API."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.alert import Alert
from app.models.user import User

router = APIRouter(prefix="/alerts", tags=["alerts"])
logger = get_logger(__name__)

_ALERT_COOLDOWN_SECONDS = 3600  # 1 hour between repeated triggers for same alert


class AlertCreate(BaseModel):
    ticker: str = Field(max_length=20)
    name: str = Field(default="", max_length=200)
    condition: Literal["above", "below", "pct_change", "drawdown"]
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
@limiter.limit("30/minute")
async def list_alerts(
    request: Request,
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
@limiter.limit("30/minute")
async def create_alert(
    request: Request,
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
@limiter.limit("30/minute")
async def patch_alert(
    request: Request,
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
@limiter.limit("30/minute")
async def delete_alert(
    request: Request,
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


def _evaluate_condition(
    alert: Alert,
    price: Decimal,
    threshold: Decimal,
    avg_prices: Optional[dict[str, Optional[Decimal]]],
    day_change_pcts: Optional[dict[str, Optional[Decimal]]],
) -> bool:
    """알림 조건별 hit 여부.

    - above/below: 현재가 vs threshold
    - pct_change : |day_change_pct| ≥ threshold(%)  (참조 데이터 없으면 미발화)
    - drawdown   : (avg - price) / avg * 100 ≥ threshold(%)  (avg 없으면 미발화)
    """
    if alert.condition == "above":
        return price >= threshold
    if alert.condition == "below":
        return price <= threshold
    if alert.condition == "pct_change":
        pct = (day_change_pcts or {}).get(alert.ticker)
        return pct is not None and abs(pct) >= threshold
    if alert.condition == "drawdown":
        avg = (avg_prices or {}).get(alert.ticker)
        if avg is None or avg <= 0:
            return False
        drop_pct = (avg - price) / avg * Decimal(100)
        return drop_pct >= threshold
    return False


def check_triggered_alerts(
    alerts: list[Alert],
    current_prices: dict[str, Optional[Decimal]],
    avg_prices: Optional[dict[str, Optional[Decimal]]] = None,
    day_change_pcts: Optional[dict[str, Optional[Decimal]]] = None,
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
        if _evaluate_condition(alert, price, threshold, avg_prices, day_change_pcts):
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
    avg_prices: Optional[dict[str, Optional[Decimal]]] = None,
    day_change_pcts: Optional[dict[str, Optional[Decimal]]] = None,
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
        if not _evaluate_condition(alert, price, threshold, avg_prices, day_change_pcts):
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
