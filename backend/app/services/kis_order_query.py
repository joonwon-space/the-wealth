"""KIS OpenAPI 주문 조회 서비스 (미체결 조회 + 체결 확인 + 주문 가능 수량).

TR_IDs:
- 국내 미체결: TTTC0084R / VTTC0084R
- 해외 미체결: TTTS3018R
- 국내 주문 가능: TTTC8908R / VTTC8908R
- 국내 체결 확인: TTTC0081R / VTTC0081R
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.services.kis_rate_limiter import acquire as _rate_limit_acquire
from app.services.kis_retry import kis_get

logger = get_logger(__name__)

_KST = timezone(timedelta(hours=9))


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


async def get_orderable_quantity(
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str,
    ticker: str,
    price: int,
    order_type: str = "BUY",
    is_paper_trading: bool = False,
    *,
    _retried: bool = False,
) -> OrderableInfo:
    """국내 주식 매수 가능 수량 조회 (TTTC8908R / VTTC8908R)."""
    from app.services.kis_token import get_kis_access_token, invalidate_kis_token

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
            await _rate_limit_acquire()
            resp = await kis_get(
                client,
                f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-psbl-order",
                headers=headers,
                params=params,
            )

        if resp.status_code in (401, 500) and not _retried:
            logger.warning(
                "KIS orderable quantity returned %d for %s — invalidating token and retrying",
                resp.status_code,
                ticker,
            )
            await invalidate_kis_token(app_key)
            return await get_orderable_quantity(
                app_key, app_secret, account_no, account_product_code,
                ticker, price, order_type, is_paper_trading, _retried=True,
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
        raise RuntimeError(f"매수 가능 수량 조회 실패 ({ticker}): {e}") from None


async def get_pending_orders(
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str,
    is_overseas: bool = False,
    is_paper_trading: bool = False,
    *,
    _retried: bool = False,
) -> list[PendingOrder]:
    """미체결 주문 조회.

    국내: TTTC0084R / VTTC0084R
    해외: TTTS3018R (모의 없음)
    """
    from app.services.kis_token import get_kis_access_token, invalidate_kis_token

    if is_overseas:
        tr_id = "TTTS3018R"
    elif is_paper_trading:
        tr_id = "VTTC0084R"
    else:
        tr_id = "TTTC0084R"

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
            await _rate_limit_acquire()
            resp = await kis_get(client, url, headers=headers, params=params)

        if resp.status_code in (401, 500) and not _retried:
            logger.warning(
                "KIS pending orders returned %d for %s — invalidating token and retrying",
                resp.status_code,
                account_no,
            )
            await invalidate_kis_token(app_key)
            return await get_pending_orders(
                app_key, app_secret, account_no, account_product_code,
                is_overseas, is_paper_trading, _retried=True,
            )

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
        raise RuntimeError(f"미체결 주문 조회 실패: {e}") from None


async def check_filled_orders(
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str,
    order_nos: list[str],
    is_paper_trading: bool = False,
    *,
    _retried: bool = False,
) -> list[FilledOrderInfo]:
    """당일 체결 내역을 조회하여 지정된 주문번호의 체결 정보를 반환.

    국내: TTTC0081R (주식일별주문체결조회) — 체결분만 조회.
    order_nos에 포함된 주문번호만 필터링하여 반환한다.
    """
    from app.services.kis_token import get_kis_access_token, invalidate_kis_token

    tr_id = "VTTC0081R" if is_paper_trading else "TTTC0081R"
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
            await _rate_limit_acquire()
            resp = await kis_get(
                client,
                f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
                headers=headers,
                params=params,
            )

        if resp.status_code in (401, 500) and not _retried:
            logger.warning(
                "KIS check_filled_orders returned %d for %s — invalidating token and retrying",
                resp.status_code,
                account_no,
            )
            await invalidate_kis_token(app_key)
            return await check_filled_orders(
                app_key, app_secret, account_no, account_product_code,
                order_nos, is_paper_trading, _retried=True,
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
        raise RuntimeError(f"체결 확인 조회 실패: {e}") from None
