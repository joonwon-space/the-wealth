"""KIS OpenAPI 주문 서비스 (국내 + 해외주식 매수/매도/취소).

Features:
- 국내/해외 주식 매수·매도
- 계좌 유형별 TR_ID 분기 (일반/ISA/연금/IRP/해외주식)
- Redis 기반 이중 주문 방지 락 (TTL 10초)
- 장 운영시간 체크 (국내 KST 09:00~15:30)
- 레이트 리밋 5회/분
- 미체결 주문 조회 / 주문 취소
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_cache import RedisCache
from app.services.kis_token import get_kis_access_token

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


@dataclass(frozen=True)
class OrderableInfo:
    """주문 가능 수량/금액 정보."""

    orderable_quantity: Decimal
    orderable_amount: Decimal
    current_price: Optional[Decimal] = field(default=None)
    currency: str = "KRW"


@dataclass(frozen=True)
class PendingOrder:
    """미체결 주문 정보."""

    order_no: str
    ticker: str
    name: str
    order_type: str  # BUY | SELL
    order_class: str  # limit | market
    quantity: Decimal
    price: Decimal
    filled_quantity: Decimal
    remaining_quantity: Decimal
    order_time: str


@dataclass(frozen=True)
class FilledOrderInfo:
    """체결 확인 결과."""

    order_no: str
    ticker: str
    order_type: str  # BUY | SELL
    filled_quantity: Decimal
    filled_price: Decimal
    total_quantity: Decimal
    is_fully_filled: bool


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
            resp = await client.post(
                f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/order-cash",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        rt_cd = data.get("rt_cd")
        if rt_cd != "0":
            msg1 = data.get("msg1", "")
            msg2 = data.get("msg2", "")
            msg = " ".join(filter(None, [msg1, msg2])) or "Unknown KIS API error"
            logger.warning(
                "KIS domestic order failed: ticker=%s rt_cd=%s msg=%s",
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
        logger.info(
            "Domestic order placed: ticker=%s order_type=%s order_no=%s",
            ticker,
            order_type,
            order_no,
        )
        return OrderResult(
            order_no=order_no,
            ticker=ticker,
            order_type=order_type,
            quantity=Decimal(quantity),
            price=price,
            status="pending",
            message=data.get("msg1", ""),
        )

    except Exception as e:
        logger.warning("Domestic order exception: ticker=%s error=%s", ticker, e)
        raise RuntimeError(f"국내 주식 주문 실패 ({ticker}): {e}") from e


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
            resp = await client.post(
                f"{settings.KIS_BASE_URL}/uapi/overseas-stock/v1/trading/order",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        rt_cd = data.get("rt_cd")
        if rt_cd != "0":
            msg1 = data.get("msg1", "")
            msg2 = data.get("msg2", "")
            msg = " ".join(filter(None, [msg1, msg2])) or "Unknown KIS API error"
            logger.warning(
                "KIS overseas order failed: ticker=%s rt_cd=%s msg=%s",
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
        logger.info(
            "Overseas order placed: ticker=%s order_type=%s order_no=%s",
            ticker,
            order_type,
            order_no,
        )
        return OrderResult(
            order_no=order_no,
            ticker=ticker,
            order_type=order_type,
            quantity=Decimal(quantity),
            price=price,
            status="pending",
            message=data.get("msg1", ""),
        )

    except Exception as e:
        logger.warning("Overseas order exception: ticker=%s error=%s", ticker, e)
        raise RuntimeError(f"해외 주식 주문 실패 ({ticker}): {e}") from e


async def get_orderable_quantity(
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str,
    ticker: str,
    price: int,
    order_type: str = "BUY",
    is_paper_trading: bool = False,
) -> OrderableInfo:
    """국내 주식 매수 가능 수량 조회 (TTTC8908R / VTTC8908R)."""
    tr_id = "VTTC8908R" if is_paper_trading else "TTTC8908R"
    token = await get_kis_access_token(app_key, app_secret)
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "Content-Type": "application/json; charset=utf-8",
    }
    params = {
        "CANO": account_no,
        "ACNT_PRDT_CD": account_product_code,
        "PDNO": ticker,
        "ORD_UNPR": str(price),
        "ORD_DVSN": "01" if price == 0 else "00",
        "CMA_EVLU_AMT_ICLD_YN": "Y",
        "OVRS_ICLD_YN": "N",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-psbl-order",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        rt_cd = data.get("rt_cd")
        if rt_cd != "0":
            msg = data.get("msg1", "Unknown KIS API error")
            raise RuntimeError(f"KIS API 오류 (rt_cd={rt_cd}): {msg}")

        output = data.get("output", {})
        return OrderableInfo(
            orderable_quantity=Decimal(str(output.get("psbl_qty", "0"))),
            orderable_amount=Decimal(str(output.get("ord_psbl_cash", "0"))),
            current_price=Decimal(str(output.get("nrcvb_buy_amt", "0"))) if output.get("nrcvb_buy_amt") else None,
            currency="KRW",
        )

    except RuntimeError:
        raise
    except Exception as e:
        logger.warning("get_orderable_quantity error: ticker=%s error=%s", ticker, e)
        raise RuntimeError(f"매수 가능 수량 조회 실패 ({ticker}): {e}") from e


async def get_pending_orders(
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str,
    is_overseas: bool = False,
    is_paper_trading: bool = False,
) -> list[PendingOrder]:
    """미체결 주문 조회.

    국내: TTTC8036R / VTTC8036R
    해외: JTTT3018R (모의 없음)
    """
    if is_overseas:
        tr_id = "JTTT3018R"
    elif is_paper_trading:
        tr_id = "VTTC8036R"
    else:
        tr_id = "TTTC8036R"

    token = await get_kis_access_token(app_key, app_secret)
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "Content-Type": "application/json; charset=utf-8",
    }

    if is_overseas:
        params = {
            "CANO": account_no,
            "ACNT_PRDT_CD": account_product_code,
            "OVRS_EXCG_CD": "NASD",
            "SORT_SQN": "DS",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": "",
        }
        url = f"{settings.KIS_BASE_URL}/uapi/overseas-stock/v1/trading/inquire-nccs"
    else:
        params = {
            "CANO": account_no,
            "ACNT_PRDT_CD": account_product_code,
            "INQR_DVSN_1": "0",
            "INQR_DVSN_2": "0",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        url = f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        rt_cd = data.get("rt_cd")
        if rt_cd != "0":
            msg = data.get("msg1", "Unknown KIS API error")
            raise RuntimeError(f"KIS API 오류 (rt_cd={rt_cd}): {msg}")

        output1: list = data.get("output1", [])
        results = []
        for item in output1:
            if is_overseas:
                qty = Decimal(str(item.get("ft_ord_qty", "0")))
                filled = Decimal(str(item.get("ft_ccld_qty", "0")))
                order_type_code = item.get("sll_buy_dvsn_cd", "02")
                order_type = "BUY" if order_type_code == "02" else "SELL"
                results.append(
                    PendingOrder(
                        order_no=item.get("odno", ""),
                        ticker=item.get("pdno", ""),
                        name=item.get("prdt_name", ""),
                        order_type=order_type,
                        order_class="limit",
                        quantity=qty,
                        price=Decimal(str(item.get("ft_ord_unpr3", "0"))),
                        filled_quantity=filled,
                        remaining_quantity=qty - filled,
                        order_time=item.get("ord_tmd", ""),
                    )
                )
            else:
                qty = Decimal(str(item.get("ord_qty", "0")))
                filled = Decimal(str(item.get("tot_ccld_qty", "0")))
                order_type_code = item.get("sll_buy_dvsn_cd", "02")
                order_type = "BUY" if order_type_code == "02" else "SELL"
                ord_dvsn = item.get("ord_dvsn_cd", "00")
                order_class = "market" if ord_dvsn == "01" else "limit"
                results.append(
                    PendingOrder(
                        order_no=item.get("odno", ""),
                        ticker=item.get("pdno", ""),
                        name=item.get("prdt_name", ""),
                        order_type=order_type,
                        order_class=order_class,
                        quantity=qty,
                        price=Decimal(str(item.get("ord_unpr", "0"))),
                        filled_quantity=filled,
                        remaining_quantity=qty - filled,
                        order_time=item.get("ord_tmd", ""),
                    )
                )
        return results

    except RuntimeError:
        raise
    except Exception as e:
        logger.warning("get_pending_orders error: %s", e)
        raise RuntimeError(f"미체결 주문 조회 실패: {e}") from e


async def cancel_order(
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str,
    order_no: str,
    ticker: str,
    quantity: int,
    price: int,
    is_overseas: bool = False,
    exchange_code: str = "",
    is_paper_trading: bool = False,
) -> bool:
    """주문 취소.

    국내: TTTC0803U / VTTC0803U
    해외: JTTT1004U
    """
    if is_overseas:
        tr_id = "JTTT1004U"
    elif is_paper_trading:
        tr_id = "VTTC0803U"
    else:
        tr_id = "TTTC0803U"

    token = await get_kis_access_token(app_key, app_secret)
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "Content-Type": "application/json; charset=utf-8",
    }

    if is_overseas:
        body = {
            "CANO": account_no,
            "ACNT_PRDT_CD": account_product_code,
            "OVRS_EXCG_CD": exchange_code,
            "PDNO": ticker,
            "ORGN_ODNO": order_no,
            "RVSE_CNCL_DVSN_CD": "02",  # 취소
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": str(price),
            "MGCO_APTM_ODNO": "",
            "ORD_SVR_DVSN_CD": "0",
        }
        url = f"{settings.KIS_BASE_URL}/uapi/overseas-stock/v1/trading/order-rvsecncl"
    else:
        body = {
            "CANO": account_no,
            "ACNT_PRDT_CD": account_product_code,
            "KRX_FWDG_ORD_ORGNO": "",
            "ORGN_ODNO": order_no,
            "ORD_DVSN": "00",
            "RVSE_CNCL_DVSN_CD": "02",  # 취소
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price),
            "QTY_ALL_ORD_YN": "Y",
        }
        url = f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/order-rvsecncl"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()

        rt_cd = data.get("rt_cd")
        if rt_cd != "0":
            msg = data.get("msg1", "Unknown KIS API error")
            logger.warning(
                "Order cancel failed: order_no=%s rt_cd=%s msg=%s",
                order_no,
                rt_cd,
                msg,
            )
            raise RuntimeError(f"주문 취소 실패 (rt_cd={rt_cd}): {msg}")

        logger.info("Order cancelled: order_no=%s ticker=%s", order_no, ticker)
        return True

    except RuntimeError:
        raise
    except Exception as e:
        logger.warning("cancel_order error: order_no=%s error=%s", order_no, e)
        raise RuntimeError(f"주문 취소 요청 실패 ({order_no}): {e}") from e


async def check_filled_orders(
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str,
    order_nos: list[str],
    is_paper_trading: bool = False,
) -> list[FilledOrderInfo]:
    """당일 체결 내역을 조회하여 지정된 주문번호의 체결 정보를 반환.

    국내: TTTC8001R (주식일별주문체결조회) — 체결분만 조회.
    order_nos에 포함된 주문번호만 필터링하여 반환한다.
    """
    tr_id = "VTTC8001R" if is_paper_trading else "TTTC8001R"
    today = datetime.now(_KST).strftime("%Y%m%d")

    token = await get_kis_access_token(app_key, app_secret)
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "Content-Type": "application/json; charset=utf-8",
    }
    params = {
        "CANO": account_no,
        "ACNT_PRDT_CD": account_product_code,
        "INQR_STRT_DT": today,
        "INQR_END_DT": today,
        "SLL_BUY_DVSN_CD": "00",  # 전체
        "INQR_DVSN": "00",
        "PDNO": "",
        "CCLD_DVSN": "01",  # 체결분만
        "ORD_GNO_BRNO": "",
        "ODNO": "",
        "INQR_DVSN_3": "00",
        "INQR_DVSN_1": "",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    order_no_set = set(order_nos)
    results: list[FilledOrderInfo] = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        rt_cd = data.get("rt_cd")
        if rt_cd != "0":
            msg = data.get("msg1", "Unknown KIS API error")
            raise RuntimeError(f"KIS 체결조회 API 오류 (rt_cd={rt_cd}): {msg}")

        for row in data.get("output1", []):
            odno = row.get("odno", "")
            if odno not in order_no_set:
                continue

            filled_qty_str = row.get("tot_ccld_qty", "0") or "0"
            filled_price_str = row.get("avg_prvs", "0") or "0"
            total_qty_str = row.get("ord_qty", "0") or "0"
            filled_qty = Decimal(filled_qty_str)
            total_qty = Decimal(total_qty_str)

            if filled_qty <= 0:
                continue

            sll_buy = row.get("sll_buy_dvsn_cd", "")
            order_type = "SELL" if sll_buy == "01" else "BUY"

            results.append(
                FilledOrderInfo(
                    order_no=odno,
                    ticker=row.get("pdno", ""),
                    order_type=order_type,
                    filled_quantity=filled_qty,
                    filled_price=Decimal(filled_price_str),
                    total_quantity=total_qty,
                    is_fully_filled=filled_qty >= total_qty,
                )
            )

        return results

    except RuntimeError:
        raise
    except Exception as e:
        logger.warning("check_filled_orders error: %s", e)
        raise RuntimeError(f"체결 확인 조회 실패: {e}") from e
