"""KIS OpenAPI 주문 취소 서비스 (국내 + 해외).

국내: TTTC0013U / VTTC0013U
해외: TTTT1004U
"""

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


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

    국내: TTTC0013U / VTTC0013U
    해외: TTTT1004U
    """
    from app.services.kis_token import get_kis_access_token

    if is_overseas:
        tr_id = "TTTT1004U"
    elif is_paper_trading:
        tr_id = "VTTC0013U"
    else:
        tr_id = "TTTC0013U"

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
        raise RuntimeError(f"주문 취소 요청 실패 ({order_no}): {e}") from None
