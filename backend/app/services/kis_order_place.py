"""KIS OpenAPI 주문 실행 서비스 (국내 + 해외 매수/매도).

Features:
- 국내/해외 주식 매수·매도
- 계좌 유형별 TR_ID 분기 (일반/ISA/연금/IRP/해외주식)
- Redis 기반 이중 주문 방지 락 (TTL 10초)
- 장 운영시간 체크 (국내 KST 09:00~15:30)
- 레이트 리밋 5회/분
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_cache import RedisCache

logger = get_logger(__name__)

_cache = RedisCache(settings.REDIS_URL)

# KST timezone
_KST = timezone(timedelta(hours=9))

# Market hours (KST)
_MARKET_OPEN = (9, 0)
_MARKET_CLOSE = (15, 30)

# Rate limiting: 5 orders per minute per user
_RATE_LIMIT_PREFIX = "order_rate:{user_id}"
_RATE_LIMIT_TTL = 60  # seconds
_RATE_LIMIT_MAX = 5

# Duplicate order prevention lock
_ORDER_LOCK_PREFIX = "order_lock:{portfolio_id}:{ticker}"
_ORDER_LOCK_TTL = 10  # seconds

# TR_ID mapping by account type
_DOMESTIC_BUY_TR_IDS = {
    "일반": "TTTC0802U",
    "ISA": "TTTC0802U",
    "연금저축": "TTTC0852U",
    "IRP": "TTTC0852U",
}
_DOMESTIC_SELL_TR_IDS = {
    "일반": "TTTC0801U",
    "ISA": "TTTC0801U",
    "연금저축": "TTTC0851U",
    "IRP": "TTTC0851U",
}

# Default TR_IDs for paper trading (virtual account)
_DOMESTIC_BUY_TR_PAPER = "VTTC0802U"
_DOMESTIC_SELL_TR_PAPER = "VTTC0801U"

# Overseas TR_IDs
_OVERSEAS_BUY_TR_ID = "JTTT1002U"
_OVERSEAS_SELL_TR_ID = "JTTT1006U"
_OVERSEAS_BUY_TR_PAPER = "VTTT1002U"
_OVERSEAS_SELL_TR_PAPER = "VTTT1001U"


@dataclass(frozen=True)
class OrderResult:
    """주문 결과."""

    order_no: str
    ticker: str
    order_type: str  # BUY | SELL
    quantity: Decimal
    price: Optional[Decimal]
    status: str  # pending | failed
    message: str = ""


def is_market_open() -> bool:
    """한국 주식 시장 운영 중 여부 (KST 평일 09:00~15:30)."""
    now = datetime.now(_KST)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    t = (now.hour, now.minute)
    return _MARKET_OPEN <= t <= _MARKET_CLOSE


def _get_domestic_tr_id(
    order_type: str,
    account_type: Optional[str],
    is_paper_trading: bool,
) -> str:
    """국내 주식 TR_ID 결정."""
    if is_paper_trading:
        return _DOMESTIC_BUY_TR_PAPER if order_type == "BUY" else _DOMESTIC_SELL_TR_PAPER
    if order_type == "BUY":
        return _DOMESTIC_BUY_TR_IDS.get(account_type or "일반", "TTTC0802U")
    return _DOMESTIC_SELL_TR_IDS.get(account_type or "일반", "TTTC0801U")


def _get_overseas_tr_id(
    order_type: str,
    is_paper_trading: bool,
) -> str:
    """해외 주식 TR_ID 결정."""
    if is_paper_trading:
        return _OVERSEAS_BUY_TR_PAPER if order_type == "BUY" else _OVERSEAS_SELL_TR_PAPER
    return _OVERSEAS_BUY_TR_ID if order_type == "BUY" else _OVERSEAS_SELL_TR_ID


async def _check_rate_limit(user_id: int) -> bool:
    """레이트 리밋 체크 (5회/분). True = 허용, False = 한도 초과."""
    key = _RATE_LIMIT_PREFIX.format(user_id=user_id)
    count_str = await _cache.get(key)
    count = int(count_str) if count_str else 0
    if count >= _RATE_LIMIT_MAX:
        return False
    await _cache.setex(key, _RATE_LIMIT_TTL, str(count + 1))
    return True


async def _acquire_order_lock(portfolio_id: int, ticker: str) -> bool:
    """이중 주문 방지 락 획득. True = 성공, False = 이미 잠김."""
    key = _ORDER_LOCK_PREFIX.format(portfolio_id=portfolio_id, ticker=ticker)
    existing = await _cache.get(key)
    if existing:
        return False
    await _cache.setex(key, _ORDER_LOCK_TTL, "1")
    return True


async def _execute_order_request(
    headers: dict[str, str],
    body: dict[str, str],
    url: str,
    ticker: str,
    order_type: str,
    quantity: int,
    price: Decimal,
    client: httpx.AsyncClient,
) -> OrderResult:
    """KIS 주문 API POST 요청을 실행하고 결과를 파싱한다.

    국내/해외 주문 공통 로직 — rate-limit·lock은 호출자가 처리한다.
    """
    resp = await client.post(url, headers=headers, json=body)
    resp.raise_for_status()
    data = resp.json()

    rt_cd = data.get("rt_cd")
    if rt_cd != "0":
        msg1 = data.get("msg1", "")
        msg2 = data.get("msg2", "")
        msg = " ".join(filter(None, [msg1, msg2])) or "Unknown KIS API error"
        logger.warning(
            "KIS order failed: ticker=%s rt_cd=%s msg=%s",
            ticker,
            rt_cd,
            msg,
        )
        return OrderResult(
            order_no="",
            ticker=ticker,
            order_type=order_type,
            quantity=Decimal(quantity),
            price=price,
            status="failed",
            message=msg,
        )

    output = data.get("output", {})
    order_no = output.get("ODNO", "")
    return OrderResult(
        order_no=order_no,
        ticker=ticker,
        order_type=order_type,
        quantity=Decimal(quantity),
        price=price,
        status="pending",
        message=data.get("msg1", ""),
    )


async def place_domestic_order(
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str,
    ticker: str,
    order_type: str,
    quantity: int,
    price: Decimal,
    order_class: str = "limit",
    account_type: Optional[str] = None,
    is_paper_trading: bool = False,
    portfolio_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> OrderResult:
    """국내 주식 매수/매도 주문.

    Args:
        order_type: "BUY" | "SELL"
        order_class: "limit" (지정가) | "market" (시장가)
        account_type: 계좌 유형 (일반/ISA/연금저축/IRP)
    """
    from app.services.kis_token import get_kis_access_token

    if user_id and not await _check_rate_limit(user_id):
        return OrderResult(
            order_no="",
            ticker=ticker,
            order_type=order_type,
            quantity=Decimal(quantity),
            price=Decimal(price),
            status="failed",
            message="주문 한도 초과: 분당 5회까지 허용됩니다.",
        )

    if portfolio_id and not await _acquire_order_lock(portfolio_id, ticker):
        return OrderResult(
            order_no="",
            ticker=ticker,
            order_type=order_type,
            quantity=Decimal(quantity),
            price=Decimal(price),
            status="failed",
            message="중복 주문 방지: 동일 종목에 대한 주문이 처리 중입니다.",
        )

    if not is_market_open():
        logger.info(
            "Order attempted outside market hours: ticker=%s order_type=%s",
            ticker,
            order_type,
        )

    tr_id = _get_domestic_tr_id(order_type, account_type, is_paper_trading)

    # ORD_DVSN: 00=지정가, 01=시장가
    ord_dvsn = "01" if order_class == "market" else "00"
    ord_price = "0" if order_class == "market" else str(price)

    token = await get_kis_access_token(app_key, app_secret)
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "Content-Type": "application/json; charset=utf-8",
    }
    body = {
        "CANO": account_no,
        "ACNT_PRDT_CD": account_product_code,
        "PDNO": ticker,
        "ORD_DVSN": ord_dvsn,
        "ORD_QTY": str(quantity),
        "ORD_UNPR": ord_price,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            result = await _execute_order_request(
                headers=headers,
                body=body,
                url=f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/order-cash",
                ticker=ticker,
                order_type=order_type,
                quantity=quantity,
                price=price,
                client=client,
            )
        if result.status == "pending":
            logger.info(
                "Domestic order placed: ticker=%s order_type=%s order_no=%s",
                ticker,
                order_type,
                result.order_no,
            )
        return result

    except Exception as e:
        logger.warning("Domestic order exception: ticker=%s error=%s", ticker, e)
        raise RuntimeError(f"국내 주식 주문 실패 ({ticker}): {e}") from None


async def place_overseas_order(
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str,
    ticker: str,
    exchange_code: str,
    order_type: str,
    quantity: int,
    price: Decimal,
    order_class: str = "limit",
    is_paper_trading: bool = False,
    portfolio_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> OrderResult:
    """해외 주식 매수/매도 주문.

    Args:
        exchange_code: 거래소 코드 (NASDAQ: NASD, NYSE: NYSE, AMEX: AMEX 등)
        order_class: "limit" (지정가) | "market" (시장가)
    """
    from app.services.kis_token import get_kis_access_token

    if user_id and not await _check_rate_limit(user_id):
        return OrderResult(
            order_no="",
            ticker=ticker,
            order_type=order_type,
            quantity=Decimal(quantity),
            price=price,
            status="failed",
            message="주문 한도 초과: 분당 5회까지 허용됩니다.",
        )

    if portfolio_id and not await _acquire_order_lock(portfolio_id, ticker):
        return OrderResult(
            order_no="",
            ticker=ticker,
            order_type=order_type,
            quantity=Decimal(quantity),
            price=price,
            status="failed",
            message="중복 주문 방지: 동일 종목에 대한 주문이 처리 중입니다.",
        )

    tr_id = _get_overseas_tr_id(order_type, is_paper_trading)

    # ORD_DVSN: 00=지정가, 00=시장가 (해외주식은 별도 처리 없음)
    ord_dvsn = "00"
    ord_price = "0" if order_class == "market" else str(price)

    token = await get_kis_access_token(app_key, app_secret)
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "Content-Type": "application/json; charset=utf-8",
    }
    body = {
        "CANO": account_no,
        "ACNT_PRDT_CD": account_product_code,
        "OVRS_EXCG_CD": exchange_code,
        "PDNO": ticker,
        "ORD_DVSN": ord_dvsn,
        "ORD_QTY": str(quantity),
        "OVRS_ORD_UNPR": ord_price,
        "ORD_SVR_DVSN_CD": "0",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            result = await _execute_order_request(
                headers=headers,
                body=body,
                url=f"{settings.KIS_BASE_URL}/uapi/overseas-stock/v1/trading/order",
                ticker=ticker,
                order_type=order_type,
                quantity=quantity,
                price=price,
                client=client,
            )
        if result.status == "pending":
            logger.info(
                "Overseas order placed: ticker=%s order_type=%s order_no=%s",
                ticker,
                order_type,
                result.order_no,
            )
        return result

    except Exception as e:
        logger.warning("Overseas order exception: ticker=%s error=%s", ticker, e)
        raise RuntimeError(f"해외 주식 주문 실패 ({ticker}): {e}") from None
