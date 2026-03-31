"""KIS 예수금 및 잔고 조회 서비스.

국내: TTTC8434R (예수금 상세현황)
해외: TTTS3012R (해외주식 체결기준잔고)
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.services.kis_token import get_kis_access_token

logger = get_logger(__name__)


@dataclass(frozen=True)
class CashBalance:
    """예수금 및 총 평가금액 정보."""

    total_cash: Decimal
    available_cash: Decimal
    total_evaluation: Decimal
    total_profit_loss: Decimal
    profit_loss_rate: Decimal
    currency: str = "KRW"
    foreign_cash: Optional[Decimal] = None
    usd_krw_rate: Optional[Decimal] = None


async def get_cash_balance(
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str = "01",
    is_overseas: bool = False,
    is_paper_trading: bool = False,
) -> CashBalance:
    """예수금 조회.

    국내: TTTC8434R (모의: VTTC8434R)
    해외: TTTS3012R (모의 없음)
    """
    if is_overseas:
        return await _get_overseas_balance(
            app_key, app_secret, account_no, account_product_code
        )
    return await _get_domestic_balance(
        app_key, app_secret, account_no, account_product_code, is_paper_trading
    )


async def _get_domestic_balance(
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str,
    is_paper_trading: bool = False,
) -> CashBalance:
    """국내 예수금 상세현황 조회 (TTTC8434R)."""
    tr_id = "VTTC8434R" if is_paper_trading else "TTTC8434R"
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
            raise RuntimeError(f"KIS API 오류 (rt_cd={rt_cd}): {msg}")

        output2: dict = (data.get("output2") or [{}])[0] if data.get("output2") else {}
        total_eval = Decimal(str(output2.get("tot_evlu_amt", "0")))
        dnca_tot_amt = Decimal(str(output2.get("dnca_tot_amt", "0")))  # 예수금 총금액 (T+0, 미체결 매수 미반영)
        nxdy_excc_amt = Decimal(str(output2.get("nxdy_excc_amt", "0")))  # 익일 정산금액 (오늘 매수 즉시 반영)
        evlu_pfls_smtl_amt = Decimal(str(output2.get("evlu_pfls_smtl_amt", "0")))
        evlu_erng_rt = Decimal(str(output2.get("evlu_erng_rt", "0")))

        # 익일 정산금액이 예수금보다 작으면 오늘 매수가 있는 것 → 익일 정산금액이 실질 잔액
        # 익일 정산금액이 0이거나 예수금보다 크면 예수금 사용 (해당 필드 미지원 계좌 대비)
        effective_cash = nxdy_excc_amt if Decimal("0") < nxdy_excc_amt <= dnca_tot_amt else dnca_tot_amt

        logger.debug(
            "Cash balance for %s: dnca_tot_amt=%s nxdy_excc_amt=%s effective=%s",
            account_no, dnca_tot_amt, nxdy_excc_amt, effective_cash,
        )

        return CashBalance(
            total_cash=effective_cash,
            available_cash=effective_cash,
            total_evaluation=total_eval,
            total_profit_loss=evlu_pfls_smtl_amt,
            profit_loss_rate=evlu_erng_rt,
            currency="KRW",
        )

    except RuntimeError:
        raise
    except Exception as e:
        logger.warning(
            "Failed to fetch domestic cash balance for %s: %s", account_no, e
        )
        raise RuntimeError(f"국내 예수금 조회 실패 ({account_no}): {e}") from e


async def _get_overseas_balance(
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str,
) -> CashBalance:
    """해외주식 체결기준잔고 조회 (TTTS3012R)."""
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
            raise RuntimeError(f"KIS 해외 API 오류 (rt_cd={rt_cd}): {msg}")

        output2: dict = data.get("output2") or {}
        tot_evlu = Decimal(str(output2.get("tot_evlu_pfls_amt", "0")))
        frcr_evlu = Decimal(str(output2.get("frcr_evlu_pfls_amt", "0")))
        ovrs_pfls = Decimal(str(output2.get("ovrs_tot_pfls", "0")))
        # 외화 현금 잔고
        frcr_buy_amt = Decimal(str(output2.get("frcr_buy_amt_smtl1", "0")))

        return CashBalance(
            total_cash=frcr_evlu,
            available_cash=frcr_evlu - frcr_buy_amt,
            total_evaluation=tot_evlu,
            total_profit_loss=ovrs_pfls,
            profit_loss_rate=Decimal("0"),
            currency="USD",
            foreign_cash=frcr_evlu,
        )

    except RuntimeError:
        raise
    except Exception as e:
        logger.warning(
            "Failed to fetch overseas cash balance for %s: %s", account_no, e
        )
        raise RuntimeError(f"해외 예수금 조회 실패 ({account_no}): {e}") from e
