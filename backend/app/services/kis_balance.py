"""KIS 예수금 및 잔고 조회 서비스.

국내: TTTC8434R (예수금 상세현황)
해외: TTTS3012R (해외주식 체결기준잔고)
해외 외화예수금: CTRP6504R (해외주식 체결기준현재잔고)
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.services.kis_rate_limiter import kis_call_slot
from app.services.kis_retry import kis_get
from app.services.kis_token import get_kis_access_token, invalidate_kis_token

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
    *,
    _retried: bool = False,
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
            async with kis_call_slot():
                resp = await kis_get(
                    client,
                    f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance",
                    headers=headers,
                    params=params,
                )

        if resp.status_code in (401, 500) and not _retried:
            logger.warning(
                "KIS domestic balance returned %d for %s — invalidating token and retrying",
                resp.status_code,
                account_no,
            )
            await invalidate_kis_token(app_key)
            return await _get_domestic_balance(
                app_key, app_secret, account_no, account_product_code,
                is_paper_trading, _retried=True,
            )

        resp.raise_for_status()
        data = resp.json()

        rt_cd = data.get("rt_cd")
        if rt_cd != "0":
            msg = data.get("msg1", "Unknown KIS API error")
            raise RuntimeError(f"KIS API 오류 (rt_cd={rt_cd}): {msg}")

        output2: dict = (data.get("output2") or [{}])[0] if data.get("output2") else {}
        total_eval = Decimal(str(output2.get("tot_evlu_amt", "0")))
        dnca_tot_amt = Decimal(str(output2.get("dnca_tot_amt", "0")))  # 예수금 총금액 (T+0)
        nxdy_excc_amt = Decimal(str(output2.get("nxdy_excc_amt", "0")))  # 익일 정산금액
        thdt_buy_amt = Decimal(str(output2.get("thdt_buy_amt", "0")))   # 금일 매수금액
        thdt_sll_amt = Decimal(str(output2.get("thdt_sll_amt", "0")))   # 금일 매도금액
        evlu_pfls_smtl_amt = Decimal(str(output2.get("evlu_pfls_smtl_amt", "0")))
        evlu_erng_rt = Decimal(str(output2.get("evlu_erng_rt", "0")))

        # 실질 잔액 계산 (우선순위):
        # 1) 0 < nxdy < dnca → KIS가 오늘 매수를 이미 반영한 익일 정산금액 사용
        # 2) nxdy >= dnca > 0 → 내일 정산 입금(매도 수익 등)이 더 많은 경우.
        #    nxdy 는 입금 예정을 포함하지만 오늘 매수는 미반영 → 수동 차감.
        # 3) nxdy = 0, thdt_buy > 0 → 연금저축 등 nxdy 미반영 계좌: 직접 계산
        # 4) 그 외 → dnca_tot_amt 그대로
        if Decimal("0") < nxdy_excc_amt < dnca_tot_amt:
            effective_cash = nxdy_excc_amt
        elif nxdy_excc_amt >= dnca_tot_amt and nxdy_excc_amt > Decimal("0"):
            effective_cash = nxdy_excc_amt - thdt_buy_amt + thdt_sll_amt
        elif thdt_buy_amt > Decimal("0"):
            effective_cash = dnca_tot_amt - thdt_buy_amt + thdt_sll_amt
        else:
            effective_cash = dnca_tot_amt

        logger.info(
            "Cash balance for %s: dnca_tot_amt=%s nxdy_excc_amt=%s "
            "thdt_buy=%s thdt_sll=%s effective=%s",
            account_no, dnca_tot_amt, nxdy_excc_amt,
            thdt_buy_amt, thdt_sll_amt, effective_cash,
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
    *,
    _retried: bool = False,
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
            async with kis_call_slot():
                resp = await kis_get(
                    client,
                    f"{settings.KIS_BASE_URL}/uapi/overseas-stock/v1/trading/inquire-balance",
                    headers=headers,
                    params=params,
                )

        if resp.status_code in (401, 500) and not _retried:
            logger.warning(
                "KIS overseas balance returned %d for %s — invalidating token and retrying",
                resp.status_code,
                account_no,
            )
            await invalidate_kis_token(app_key)
            return await _get_overseas_balance(
                app_key, app_secret, account_no, account_product_code,
                _retried=True,
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


@dataclass(frozen=True)
class OverseasPresentBalance:
    """CTRP6504R 응답에서 추출한 USD 외화예수금 + 환율."""

    usd_cash: Decimal
    usd_krw_rate: Decimal


async def get_overseas_present_balance(
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str = "01",
    *,
    _retried: bool = False,
) -> OverseasPresentBalance:
    """해외주식 체결기준현재잔고 조회 (CTRP6504R) — USD 외화예수금/환율 추출.

    TTTS3012R 의 output2 에는 외화 예수금(`frcr_dncl_amt`) 필드가 없어,
    해외주식 위주의 계좌에서 USD cash 가 노출되지 않는다. CTRP6504R 은
    통화별로 외화예수금/환율을 함께 내려주므로, USD row 만 골라 사용한다.

    실패 시 RuntimeError 를 raise — 호출 측에서 graceful fallback 한다.
    """
    token = await get_kis_access_token(app_key, app_secret)
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "CTRP6504R",
        "Content-Type": "application/json; charset=utf-8",
    }
    params = {
        "CANO": account_no,
        "ACNT_PRDT_CD": account_product_code,
        "WCRC_FRCR_DVSN_CD": "02",  # 02 = 외화
        "NATN_CD": "000",            # 전체
        "TR_MKET_CD": "00",          # 전체
        "INQR_DVSN_CD": "00",        # 전체
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            async with kis_call_slot():
                resp = await kis_get(
                    client,
                    f"{settings.KIS_BASE_URL}/uapi/overseas-stock/v1/trading/inquire-present-balance",
                    headers=headers,
                    params=params,
                )

        if resp.status_code in (401, 500) and not _retried:
            logger.warning(
                "KIS overseas present-balance returned %d for %s — invalidating token and retrying",
                resp.status_code,
                account_no,
            )
            await invalidate_kis_token(app_key)
            return await get_overseas_present_balance(
                app_key, app_secret, account_no, account_product_code,
                _retried=True,
            )

        resp.raise_for_status()
        data = resp.json()

        rt_cd = data.get("rt_cd")
        if rt_cd != "0":
            msg = data.get("msg1", "Unknown KIS API error")
            raise RuntimeError(f"KIS 해외 현재잔고 오류 (rt_cd={rt_cd}): {msg}")

        usd_cash = Decimal("0")
        usd_rate = Decimal("0")
        for row in (data.get("output2") or []):
            if (row.get("crcy_cd") or "").upper() != "USD":
                continue
            usd_cash = Decimal(str(row.get("frcr_dncl_amt_2") or "0"))
            usd_rate = Decimal(str(row.get("frst_bltn_exrt") or "0"))
            break

        return OverseasPresentBalance(usd_cash=usd_cash, usd_krw_rate=usd_rate)

    except RuntimeError:
        raise
    except Exception as e:
        logger.warning(
            "Failed to fetch overseas present-balance for %s: %s", account_no, e
        )
        raise RuntimeError(f"해외 현재잔고 조회 실패 ({account_no}): {e}") from e
