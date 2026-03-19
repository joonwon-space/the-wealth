"""KIS OpenAPI 계좌 잔고 조회 및 Reconciliation."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.services.kis_token import get_kis_access_token

logger = get_logger(__name__)


@dataclass(frozen=True)
class KisHolding:
    ticker: str
    name: str
    quantity: Decimal
    avg_price: Decimal
    market: Optional[str] = field(default=None)


async def fetch_account_holdings(
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str = "01",
) -> list[KisHolding]:
    """KIS 계좌 잔고 조회 (TTTC8434R).

    NOTE: 실제 계좌번호가 필요합니다. docs/plan/manual-tasks.md 참고.
    """
    token = await get_kis_access_token(app_key, app_secret)
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "TTTC8434R",
        "Content-Type": "application/json; charset=utf-8",
    }
    params = {
        "CANO": account_no,
        "ACNT_PRDT_CD": account_product_code,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        rt_cd = data.get("rt_cd")
        if rt_cd != "0":
            msg = data.get("msg1", "Unknown KIS API error")
            logger.warning(
                "KIS API error for %s-%s: rt_cd=%s msg=%s",
                account_no,
                account_product_code,
                rt_cd,
                msg,
            )
            return []

        output1: list = data.get("output1", [])
        result = []
        for item in output1:
            qty = Decimal(str(item.get("hldg_qty", "0")))
            if qty <= 0:
                continue
            result.append(
                KisHolding(
                    ticker=item.get("pdno", ""),
                    name=item.get("prdt_name", ""),
                    quantity=qty,
                    avg_price=Decimal(str(item.get("pchs_avg_pric", "0"))),
                )
            )
        return result
    except Exception as e:
        logger.warning(
            "Failed to fetch KIS account holdings for %s-%s: %s",
            account_no,
            account_product_code,
            e,
        )
        return []


async def fetch_overseas_account_holdings(
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str = "01",
) -> tuple[list[KisHolding], dict]:
    """KIS 해외주식 잔고 조회 (TTTS3012R).

    Returns (holdings, output2_summary) where summary contains USD totals:
    - ovrs_tot_pfls: 해외주식 평가손익합계 (USD)
    - frcr_evlu_pfls_amt: 해외주식 평가금액 (USD)
    - tot_evlu_pfls_amt: 전체 평가손익 (USD)
    """
    token = await get_kis_access_token(app_key, app_secret)
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "TTTS3012R",
        "Content-Type": "application/json; charset=utf-8",
    }
    params = {
        "CANO": account_no,
        "ACNT_PRDT_CD": account_product_code,
        "OVRS_EXCG_CD": "",
        "TR_CRCY_CD": "USD",
        "INQR_DVSN_CD": "00",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "OFL_YN": "",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": "",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.KIS_BASE_URL}/uapi/overseas-stock/v1/trading/inquire-balance",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        rt_cd = data.get("rt_cd")
        if rt_cd != "0":
            msg = data.get("msg1", "Unknown KIS API error")
            logger.warning(
                "KIS overseas API error for %s-%s: rt_cd=%s msg=%s",
                account_no,
                account_product_code,
                rt_cd,
                msg,
            )
            return [], {}

        output1: list = data.get("output1", [])
        result = []
        for item in output1:
            qty = Decimal(str(item.get("ovrs_cblc_qty", "0")))
            if qty <= 0:
                continue
            result.append(
                KisHolding(
                    ticker=item.get("ovrs_pdno", ""),
                    name=item.get("ovrs_item_name", ""),
                    quantity=qty,
                    avg_price=Decimal(str(item.get("pchs_avg_pric", "0"))),
                    market=item.get("ovrs_excg_cd") or None,
                )
            )
        return result, data.get("output2") or {}
    except Exception as e:
        logger.warning(
            "Failed to fetch KIS overseas account holdings for %s-%s: %s",
            account_no,
            account_product_code,
            e,
        )
        return [], {}
