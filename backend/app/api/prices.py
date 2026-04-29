"""가격 히스토리 및 SSE 실시간 가격 API."""

import asyncio
import json
import time
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
from app.core.ticker import is_domestic
from app.services.kis_price import (
    fetch_and_cache_domestic_price,
    get_or_fetch_overseas_price,
)

router = APIRouter(prefix="/prices", tags=["prices"])
logger = get_logger(__name__)

_KST = timezone(timedelta(hours=9))
_MARKET_OPEN = (9, 0)    # KST 09:00
_MARKET_CLOSE = (15, 30)  # KST 15:30
_SSE_INTERVAL = 30         # seconds between price fetches
_SSE_HEARTBEAT = 15        # seconds between heartbeat pings
_SSE_TIMEOUT = 7200        # 2 hour max connection duration
_SSE_MAX_CONNECTIONS = 3   # max concurrent SSE connections per user
_SSE_TICKER_CACHE_TTL = 60  # seconds to cache ticker list per user

# Global shutdown event — set during lifespan shutdown to terminate SSE streams
_shutdown_event: asyncio.Event = asyncio.Event()

# Per-user active SSE connection count {user_id: count}
_active_connections: dict[int, int] = {}
_connections_lock: asyncio.Lock = asyncio.Lock()

# Per-user ticker list cache {user_id: (ticker_market_map, cached_at_monotonic)}
# ticker_market_map: {ticker: market}
_ticker_cache: dict[int, tuple[dict[str, str], float]] = {}
_ticker_cache_lock: asyncio.Lock = asyncio.Lock()


async def _get_cached_ticker_market_map(
    user_id: int, portfolio_ids: list[int]
) -> dict[str, str]:
    """SSE 루프에서 사용하는 ticker→market 맵을 60초 TTL로 메모리 캐시."""
    async with _ticker_cache_lock:
        if user_id in _ticker_cache:
            ticker_map, cached_at = _ticker_cache[user_id]
            if time.monotonic() - cached_at < _SSE_TICKER_CACHE_TTL:
                return ticker_map

    async with AsyncSessionLocal() as db:
        hold_result = await db.execute(
            select(Holding.ticker, Holding.market).distinct().where(
                Holding.portfolio_id.in_(portfolio_ids)
            )
        )
        ticker_map = {row[0]: (row[1] or "NYSE") for row in hold_result.all()}

    async with _ticker_cache_lock:
        _ticker_cache[user_id] = (ticker_map, time.monotonic())

    return ticker_map


async def invalidate_sse_ticker_cache(user_id: int) -> None:
    """sync 또는 holding 변경 후 SSE ticker 캐시 무효화."""
    async with _ticker_cache_lock:
        _ticker_cache.pop(user_id, None)


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


_ALERT_REFRESH_INTERVAL = 300  # refresh alert cache every 5 minutes


async def _load_active_alerts(user_id: int) -> list[Alert]:
    """DB에서 사용자의 활성 알림을 조회한다."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Alert).where(
                    Alert.user_id == user_id,
                    Alert.is_active.is_(True),
                )
            )
            return list(result.scalars().all())
    except Exception as exc:
        logger.warning("Alert load error for user %s: %s", user_id, exc)
        return []


async def _check_alerts_and_emit(
    user_id: int,
    prices: dict[str, str],
    alerts: list[Alert],
    avg_prices: Optional[dict[str, Optional[Decimal]]] = None,
) -> Optional[str]:
    """활성 알림을 가격과 비교해 트리거된 알림 SSE 이벤트 문자열 반환.

    - alerts: 호출자가 관리하는 인메모리 알림 목록 (per-tick DB 조회 제거).
    - avg_prices: ticker → 평균 매입가 dict. drawdown 조건 평가에 필요.
      pct_change 조건은 day_change_pcts 가 필요하지만 SSE 는 detail fetch 추가
      비용을 피하려 dashboard 30s tick 경로에 위임 (real-time SSE 에서는 미발화).
    - 트리거된 알림은 last_triggered_at 기록 및 is_active=False 처리.
    - 트리거 없으면 None 반환.
    """
    if not alerts:
        return None
    try:
        decimal_prices: dict[str, Optional[Decimal]] = {
            ticker: Decimal(price_str) for ticker, price_str in prices.items()
        }
        triggered = check_and_dedup_alerts(alerts, decimal_prices, avg_prices=avg_prices)

        if triggered:
            from app.services.push_sender import PushPayload, send_push

            async with AsyncSessionLocal() as db:
                # Create notification records for each triggered alert
                push_payloads: list[PushPayload] = []
                for alert_data in triggered:
                    cond = alert_data["condition"]
                    label = alert_data['name'] or alert_data['ticker']
                    if cond == "above":
                        title = f"{label} 목표가 도달"
                        body = (
                            f"{alert_data['ticker']} 현재가 {alert_data['current_price']:,.0f}이 "
                            f"목표가 {alert_data['threshold']:,.0f} 이상에 도달했습니다."
                        )
                    elif cond == "below":
                        title = f"{label} 목표가 도달"
                        body = (
                            f"{alert_data['ticker']} 현재가 {alert_data['current_price']:,.0f}이 "
                            f"목표가 {alert_data['threshold']:,.0f} 이하에 도달했습니다."
                        )
                    elif cond == "drawdown":
                        title = f"{label} 평균단가 대비 하락"
                        body = (
                            f"{alert_data['ticker']} 가 평균단가 대비 "
                            f"{alert_data['threshold']:.2f}% 이상 하락했습니다 "
                            f"(현재가 {alert_data['current_price']:,.0f})."
                        )
                    else:  # pct_change — SSE 경로에서는 미발화 가정이지만 방어적 처리
                        title = f"{label} 일일 변동 알림"
                        body = (
                            f"{alert_data['ticker']} 일일 변동이 "
                            f"±{alert_data['threshold']:.2f}% 이상 발생했습니다."
                        )
                    notification = Notification(
                        user_id=user_id,
                        type="alert_triggered",
                        title=title,
                        body=body,
                    )
                    db.add(notification)
                    push_payloads.append(
                        PushPayload(
                            title=title,
                            body=body,
                            url=f"/dashboard/stocks/{alert_data['ticker']}",
                            tag=f"alert:{alert_data['ticker']}",
                        )
                    )
                await db.commit()

                # Fan out to any registered Web Push subscriptions. send_push
                # is a no-op when VAPID keys aren't configured, so this is
                # safe in dev.
                for payload in push_payloads:
                    try:
                        await send_push(db, user_id, payload)
                    except Exception as push_exc:  # noqa: BLE001
                        logger.warning("push_sender failed: %s", push_exc)
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

                # ticker → 평균 매입가 (drawdown 알림 평가용). 같은 ticker 가
                # 여러 portfolio 에 걸쳐 있으면 quantity 가중 평균.
                avg_prices: dict[str, Optional[Decimal]] = {}
                if portfolio_ids:
                    hold_result = await db.execute(
                        select(Holding).where(Holding.portfolio_id.in_(portfolio_ids))
                    )
                    qty_value: dict[str, Decimal] = {}
                    qty_total: dict[str, Decimal] = {}
                    for h in hold_result.scalars().all():
                        qty = Decimal(str(h.quantity))
                        avg = Decimal(str(h.avg_price))
                        qty_value[h.ticker] = qty_value.get(h.ticker, Decimal(0)) + qty * avg
                        qty_total[h.ticker] = qty_total.get(h.ticker, Decimal(0)) + qty
                    for ticker, total in qty_total.items():
                        avg_prices[ticker] = (
                            (qty_value[ticker] / total) if total > 0 else None
                        )

            if not portfolio_ids or not acct:
                yield "data: {\"error\": \"no_data\"}\n\n"
                return

            app_key = decrypt(acct.app_key_enc)
            app_secret = decrypt(acct.app_secret_enc)

            # 연결 시 알림 목록 로드 (5분마다 갱신)
            active_alerts: list[Alert] = await _load_active_alerts(current_user.id)
            last_alert_refresh = time.monotonic()

            async with httpx.AsyncClient(timeout=10.0) as client:
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
                        ticker_market_map = await _get_cached_ticker_market_map(
                            current_user.id, portfolio_ids
                        )

                        if not ticker_market_map:
                            yield f"data: {json.dumps({'prices': {}})}\n\n"
                        else:
                            domestic = [t for t in ticker_market_map if is_domestic(t)]
                            overseas = [t for t in ticker_market_map if not is_domestic(t)]

                            domestic_results = await asyncio.gather(
                                *[fetch_and_cache_domestic_price(t, app_key, app_secret, client) for t in domestic],
                                return_exceptions=True,
                            )
                            overseas_results = await asyncio.gather(
                                *[
                                    get_or_fetch_overseas_price(
                                        t, ticker_market_map[t], app_key, app_secret, client
                                    )
                                    for t in overseas
                                ],
                                return_exceptions=True,
                            )

                            prices: dict[str, str] = {}
                            for ticker, price in zip(domestic, domestic_results):
                                if isinstance(price, Decimal) and price > 0:
                                    prices[ticker] = str(price)
                            for ticker, price in zip(overseas, overseas_results):
                                if isinstance(price, Decimal) and price > 0:
                                    prices[ticker] = str(price)

                            yield f"data: {json.dumps({'market_open': True, 'prices': prices})}\n\n"

                            # 5분마다 알림 목록 갱신
                            now_mono = time.monotonic()
                            if now_mono - last_alert_refresh >= _ALERT_REFRESH_INTERVAL:
                                active_alerts = await _load_active_alerts(current_user.id)
                                last_alert_refresh = now_mono

                            # Check alerts and emit triggered events
                            alert_event = await _check_alerts_and_emit(
                                current_user.id, prices, active_alerts, avg_prices
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
