"""KIS API 체결 내역 조회 서비스 (국내 + 해외주식).

국내: TTTC8001R (주식일별주문체결조회)
해외: TTTS3035R (해외주식 주문체결내역)
"""

from datetime import datetime

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.services.kis_rate_limiter import kis_call_slot
from app.services.kis_retry import kis_get
from app.services.kis_token import get_kis_access_token

logger = get_logger(__name__)


async def _get_headers(app_key: str, app_secret: str, tr_id: str) -> dict:
    token = await get_kis_access_token(app_key, app_secret)
    return {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "Content-Type": "application/json; charset=utf-8",
    }


async def fetch_domestic_transactions(
    app_key: str,
    app_secret: str,
    account_no: str,
    acnt_prdt_cd: str,
    from_date: str,
    to_date: str,
    client: httpx.AsyncClient,
) -> list[dict]:
    """국내주식 체결 내역 조회 (TTTC8001R).

    from_date, to_date: YYYYMMDD 형식
    """
    headers = await _get_headers(app_key, app_secret, "TTTC8001R")
    params = {
        "CANO": account_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "INQR_STRT_DT": from_date,
        "INQR_END_DT": to_date,
        "SLL_BUY_DVSN_CD": "00",  # 전체(매도+매수)
        "INQR_DVSN": "00",
        "PDNO": "",
        "CCLD_DVSN": "01",        # 체결만
        "ORD_GNO_BRNO": "",
        "ODNO": "",
        "INQR_DVSN_3": "00",
        "INQR_DVSN_1": "",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    results: list[dict] = []
    try:
        async with kis_call_slot():
            resp = await kis_get(
                client,
                f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
                headers=headers,
                params=params,
            )
        resp.raise_for_status()
        data = resp.json()
        for row in data.get("output1", []):
            qty_str = row.get("tot_ccld_qty", "0") or "0"
            price_str = row.get("avg_prvs", "0") or "0"
            if not qty_str or qty_str == "0":
                continue
            sll_buy = row.get("sll_buy_dvsn_cd", "")
            tx_type = "SELL" if sll_buy == "01" else "BUY"
            traded_at_str = row.get("ord_dt", "") + row.get("ord_tmd", "000000")
            try:
                traded_at = datetime.strptime(traded_at_str[:14], "%Y%m%d%H%M%S").isoformat()
            except (ValueError, TypeError):
                traded_at = row.get("ord_dt", "")
            results.append({
                "ticker": row.get("pdno", ""),
                "name": row.get("prdt_name", ""),
                "type": tx_type,
                "quantity": qty_str,
                "price": price_str,
                "total_amount": str(float(qty_str) * float(price_str)),
                "traded_at": traded_at,
                "market": "domestic",
            })
    except Exception as e:
        logger.warning("Failed to fetch domestic transactions: %s", e)
    return results


_OVERSEAS_EXCHANGES = ["NASD", "NYSE", "AMEX", "SEHK", "TKSE", "SHAA", "SZAA", "HASE", "VNSE"]


async def _fetch_overseas_transactions_by_exchange(
    app_key: str,
    app_secret: str,
    account_no: str,
    acnt_prdt_cd: str,
    from_date: str,
    to_date: str,
    exchange: str,
    client: httpx.AsyncClient,
) -> list[dict]:
    headers = await _get_headers(app_key, app_secret, "TTTS3035R")
    params = {
        "CANO": account_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "PDNO": "",
        "ORD_STRT_DT": from_date,
        "ORD_END_DT": to_date,
        "SLL_BUY_DVSN_CD": "00",
        "CCLD_NCCS_DVSN": "01",  # 체결만
        "OVRS_EXCG_CD": exchange,
        "SORT_SQN": "DS",
        "CTX_AREA_NK200": "",
        "CTX_AREA_FK200": "",
    }
    results: list[dict] = []
    try:
        async with kis_call_slot():
            resp = await kis_get(
                client,
                f"{settings.KIS_BASE_URL}/uapi/overseas-stock/v1/trading/inquire-ccnl",
                headers=headers,
                params=params,
            )
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("output") or []
        logger.debug("Overseas tx [%s] rt_cd=%s rows=%d", exchange, data.get("rt_cd"), len(rows))
        for row in rows:
            qty_str = row.get("ft_ccld_qty", "0") or "0"
            price_str = row.get("ft_ccld_unpr3", "0") or "0"
            if not qty_str or qty_str == "0":
                continue
            sll_buy = row.get("sll_buy_dvsn_cd", "")
            tx_type = "SELL" if sll_buy == "01" else "BUY"
            traded_at_str = row.get("ord_dt", "") + row.get("ord_tmd", "000000")
            try:
                traded_at = datetime.strptime(traded_at_str[:14], "%Y%m%d%H%M%S").isoformat()
            except (ValueError, TypeError):
                traded_at = row.get("ord_dt", "")
            total = float(qty_str) * float(price_str)
            results.append({
                "ticker": row.get("pdno", ""),
                "name": row.get("prdt_name", ""),
                "type": tx_type,
                "quantity": qty_str,
                "price": price_str,
                "total_amount": str(total),
                "traded_at": traded_at,
                "market": row.get("ovrs_excg_cd", exchange),
            })
    except Exception as e:
        logger.warning("Failed to fetch overseas transactions [%s]: %s", exchange, e)
    return results


async def fetch_overseas_transactions(
    app_key: str,
    app_secret: str,
    account_no: str,
    acnt_prdt_cd: str,
    from_date: str,
    to_date: str,
    client: httpx.AsyncClient,
) -> list[dict]:
    """해외주식 체결 내역 조회 (TTTS3035R) — 거래소별 병렬 조회.

    from_date, to_date: YYYYMMDD 형식
    """
    import asyncio as _asyncio

    tasks = [
        _fetch_overseas_transactions_by_exchange(
            app_key, app_secret, account_no, acnt_prdt_cd,
            from_date, to_date, exch, client,
        )
        for exch in _OVERSEAS_EXCHANGES
    ]
    results_per_exchange = await _asyncio.gather(*tasks, return_exceptions=True)
    combined: list[dict] = []
    for res in results_per_exchange:
        if isinstance(res, list):
            combined.extend(res)
    return combined
