"""가격 히스토리 및 SSE 실시간 가격 API."""

import asyncio
import json
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.alerts import check_and_dedup_alerts
from app.api.deps import get_current_user, get_current_user_sse
from app.core.encryption import decrypt
from app.db.session import AsyncSessionLocal, get_db
from app.models.alert import Alert
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.notification import Notification
from app.models.portfolio import Portfolio
from app.models.price_snapshot import PriceSnapshot
from app.models.user import User
from app.core.logging import get_logger
from app.services.kis_price import fetch_domestic_price

router = APIRouter(prefix="/prices", tags=["prices"])
logger = get_logger(__name__)

_KST = timezone(timedelta(hours=9))
_MARKET_OPEN = (9, 0)    # KST 09:00
_MARKET_CLOSE = (15, 30)  # KST 15:30
_SSE_INTERVAL = 30         # seconds between price fetches
_SSE_HEARTBEAT = 15        # seconds between heartbeat pings
_SSE_TIMEOUT = 7200        # 2 hour max connection duration
_SSE_MAX_CONNECTIONS = 3   # max concurrent SSE connections per user

# Global shutdown event — set during lifespan shutdown to terminate SSE streams
_shutdown_event: asyncio.Event = asyncio.Event()

# Per-user active SSE connection count {user_id: count}
_active_connections: dict[int, int] = {}
_connections_lock: asyncio.Lock = asyncio.Lock()


def signal_sse_shutdown() -> None:
    """Signal all active SSE connections to close gracefully."""
    _shutdown_event.set()


def _is_market_open() -> bool:
    now = datetime.now(_KST)
    if now.weekday() >= 5:
        return False
    t = (now.hour, now.minute)
    return _MARKET_OPEN <= t <= _MARKET_CLOSE


async def _increment_connection(user_id: int) -> bool:
    """Increment connection count for user. Returns True if allowed, False if limit exceeded."""
    async with _connections_lock:
        count = _active_connections.get(user_id, 0)
        if count >= _SSE_MAX_CONNECTIONS:
            return False
        _active_connections[user_id] = count + 1
        return True


async def _decrement_connection(user_id: int) -> None:
    """Decrement connection count for user."""
    async with _connections_lock:
        count = _active_connections.get(user_id, 0)
        if count <= 1:
            _active_connections.pop(user_id, None)
        else:
            _active_connections[user_id] = count - 1


async def _check_alerts_and_emit(
    user_id: int,
    prices: dict[str, str],
) -> Optional[str]:
    """활성 알림을 가격과 비교해 트리거된 알림 SSE 이벤트 문자열 반환.

    - 트리거된 알림은 last_triggered_at 기록 및 is_active=False 처리.
    - 트리거 없으면 None 반환.
    """
    try:
        decimal_prices: dict[str, Optional[Decimal]] = {
            ticker: Decimal(price_str) for ticker, price_str in prices.items()
        }
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Alert).where(
                    Alert.user_id == user_id,
                    Alert.is_active.is_(True),
                )
            )
            alerts = list(result.scalars().all())

            if not alerts:
                return None

            triggered = check_and_dedup_alerts(alerts, decimal_prices)

            if triggered:
                # Create notification records for each triggered alert
                for alert_data in triggered:
                    condition_kr = "이상" if alert_data["condition"] == "above" else "이하"
                    notification = Notification(
                        user_id=user_id,
                        type="alert_triggered",
                        title=f"{alert_data['name'] or alert_data['ticker']} 목표가 도달",
                        body=(
                            f"{alert_data['ticker']} 현재가 {alert_data['current_price']:,.0f}이 "
                            f"목표가 {alert_data['threshold']:,.0f}{condition_kr}에 도달했습니다."
                        ),
                    )
                    db.add(notification)
                await db.commit()
                return f"event: alerts\ndata: {json.dumps(triggered)}\n\n"
    except Exception as exc:
        logger.warning("Alert check error for user %s: %s", user_id, exc)
    return None


@router.get("/{ticker}/history")
async def get_price_history(
    ticker: str,
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    limit: int = Query(90, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """종목 일별 종가 히스토리 조회.

    - `from`: 시작일 (inclusive), 기본값 없음
    - `to`: 종료일 (inclusive), 기본값 없음
    - `limit`: 최대 반환 건수 (기본 90일, 최대 365일)
    """
    stmt = (
        select(PriceSnapshot)
        .where(PriceSnapshot.ticker == ticker.upper())
        .order_by(PriceSnapshot.snapshot_date.desc())
        .limit(limit)
    )
    if from_date:
        stmt = stmt.where(PriceSnapshot.snapshot_date >= from_date)
    if to_date:
        stmt = stmt.where(PriceSnapshot.snapshot_date <= to_date)

    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    return [
        {
            "date": snap.snapshot_date.isoformat(),
            "open": str(Decimal(str(snap.open))) if snap.open is not None else None,
            "high": str(Decimal(str(snap.high))) if snap.high is not None else None,
            "low": str(Decimal(str(snap.low))) if snap.low is not None else None,
            "close": str(Decimal(str(snap.close))),
            "volume": snap.volume,
        }
        for snap in sorted(snapshots, key=lambda s: s.snapshot_date)
    ]


@router.get("/stream")
async def stream_prices(
    current_user: User = Depends(get_current_user_sse),
) -> StreamingResponse:
    """보유 종목 현재가 SSE 스트림.

    30초 간격으로 가격을 push한다. 시장 미개장 시 상태만 전송.
    15초마다 heartbeat ping을 전송한다.
    최대 연결 시간 2시간. 사용자당 최대 3개 동시 연결.
    알림 조건 충족 시 `event: alerts` 이벤트를 함께 전송한다.
    """
    allowed = await _increment_connection(current_user.id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Too many SSE connections. Max {_SSE_MAX_CONNECTIONS} per user.",
        )

    async def event_generator():
        try:
            elapsed = 0
            async with AsyncSessionLocal() as db:
                # 보유 종목 + KIS 계정 조회
                port_result = await db.execute(
                    select(Portfolio).where(Portfolio.user_id == current_user.id)
                )
                portfolio_ids = [p.id for p in port_result.scalars().all()]

                acct_result = await db.execute(
                    select(KisAccount).where(KisAccount.user_id == current_user.id).limit(1)
                )
                acct = acct_result.scalar_one_or_none()

            if not portfolio_ids or not acct:
                yield "data: {\"error\": \"no_data\"}\n\n"
                return

            app_key = decrypt(acct.app_key_enc)
            app_secret = decrypt(acct.app_secret_enc)

            while elapsed < _SSE_TIMEOUT and not _shutdown_event.is_set():
                if not _is_market_open():
                    yield f"data: {json.dumps({'market_open': False})}\n\n"
                    # Send heartbeat pings while waiting for next cycle
                    remaining = _SSE_INTERVAL
                    while remaining > 0 and not _shutdown_event.is_set():
                        wait = min(_SSE_HEARTBEAT, remaining)
                        try:
                            await asyncio.wait_for(
                                _shutdown_event.wait(), timeout=wait
                            )
                            break  # Shutdown signaled
                        except asyncio.TimeoutError:
                            pass
                        remaining -= wait
                        if remaining > 0:
                            yield ": ping\n\n"
                    if _shutdown_event.is_set():
                        break
                    elapsed += _SSE_INTERVAL
                    continue

                try:
                    async with AsyncSessionLocal() as db:
                        hold_result = await db.execute(
                            select(Holding.ticker).distinct().where(
                                Holding.portfolio_id.in_(portfolio_ids)
                            )
                        )
                        tickers = [r[0] for r in hold_result.all()]

                    if not tickers:
                        yield f"data: {json.dumps({'prices': {}})}\n\n"
                    else:
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            results = await asyncio.gather(
                                *[fetch_domestic_price(t, app_key, app_secret, client) for t in tickers],
                                return_exceptions=True,
                            )
                        prices = {
                            ticker: str(price)
                            for ticker, price in zip(tickers, results)
                            if isinstance(price, Decimal) and price > 0
                        }
                        yield f"data: {json.dumps({'market_open': True, 'prices': prices})}\n\n"

                        # Check alerts and emit triggered events
                        alert_event = await _check_alerts_and_emit(
                            current_user.id, prices
                        )
                        if alert_event:
                            yield alert_event

                except Exception as e:
                    logger.warning("SSE price fetch error: %s", e)
                    yield f"data: {json.dumps({'error': 'fetch_failed'})}\n\n"

                # Wait for next interval with heartbeat pings
                remaining = _SSE_INTERVAL
                while remaining > 0 and not _shutdown_event.is_set():
                    wait = min(_SSE_HEARTBEAT, remaining)
                    try:
                        await asyncio.wait_for(
                            _shutdown_event.wait(), timeout=wait
                        )
                        break  # Shutdown signaled
                    except asyncio.TimeoutError:
                        pass
                    remaining -= wait
                    if remaining > 0:
                        yield ": ping\n\n"

                if _shutdown_event.is_set():
                    break
                elapsed += _SSE_INTERVAL

            if elapsed >= _SSE_TIMEOUT:
                logger.info(
                    "SSE stream closed: max duration reached for user %s", current_user.id
                )
                yield f"data: {json.dumps({'close': 'max_duration'})}\n\n"
            elif _shutdown_event.is_set():
                logger.info("SSE stream closed due to server shutdown")
        finally:
            await _decrement_connection(current_user.id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
