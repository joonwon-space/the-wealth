"""KIS 계좌 단위 예수금/평가금액 집계 — 사용자의 모든 KIS 계좌 합산.

`/dashboard/cash-summary` 및 향후 다른 집계 화면에서 재사용한다.
KIS API 호출 결과는 계좌별로 30초간 Redis 캐시되며, 부분 실패는
per-account `error` 필드로 노출되어 전체 응답이 502 가 되지 않는다.
"""

import asyncio
import json
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import decrypt
from app.core.logging import get_logger
from app.core.redis_cache import RedisCache
from app.models.kis_account import KisAccount
from app.models.user import User
from app.schemas.dashboard import CashSummaryAccount, CashSummaryResponse
from app.services.kis_account import fetch_overseas_account_holdings
from app.services.kis_balance import (
    get_cash_balance,
    get_overseas_present_balance,
)
from app.services.kis_fx import get_exchange_rate

logger = get_logger(__name__)

_cache = RedisCache(settings.REDIS_URL)

# 계좌 단위 캐시: 단일 KIS 계좌의 cash balance 계산 결과 (30초)
ACCOUNT_CACHE_PREFIX = "cash_balance:account:{account_id}"
ACCOUNT_CACHE_TTL = 30

# 사용자 단위 캐시: aggregate 응답 전체 (30초)
USER_SUMMARY_CACHE_PREFIX = "cash_summary:user:{user_id}"
USER_SUMMARY_CACHE_TTL = 30

_ZERO = Decimal("0")


def _decimal_or_none(value: Optional[str]) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(value)
    except (TypeError, ValueError):
        return None


def _serialize_account(account: CashSummaryAccount) -> str:
    payload = account.model_dump()
    payload = {
        k: (str(v) if isinstance(v, Decimal) else v) for k, v in payload.items()
    }
    return json.dumps(payload)


def _deserialize_account(raw: str) -> CashSummaryAccount:
    data = json.loads(raw)
    for field in (
        "total_cash",
        "available_cash",
        "total_evaluation",
        "total_profit_loss",
        "foreign_cash",
        "usd_krw_rate",
    ):
        data[field] = _decimal_or_none(data.get(field))
    return CashSummaryAccount(**data)


async def fetch_cash_balance_for_account(acct: KisAccount) -> CashSummaryAccount:
    """단일 KIS 계좌의 예수금/평가금액 조회.

    Redis 캐시 hit 시 KIS API 를 호출하지 않는다. KIS 호출이 실패하면
    `error` 필드를 채워 반환한다 (raise 하지 않음 → 다른 계좌 처리 영향 없음).
    """
    cache_key = ACCOUNT_CACHE_PREFIX.format(account_id=acct.id)
    cached = await _cache.get(cache_key)
    if cached:
        try:
            return _deserialize_account(cached)
        except (ValueError, KeyError) as e:
            logger.warning(
                "Stale/invalid cache for KIS account %s: %s — refetching",
                acct.id,
                e,
            )

    try:
        app_key = decrypt(acct.app_key_enc)
        app_secret = decrypt(acct.app_secret_enc)
    except Exception as e:
        logger.warning("Failed to decrypt KIS credentials for account %s: %s", acct.id, e)
        return CashSummaryAccount(
            kis_account_id=acct.id,
            label=acct.label,
            error="자격증명 복호화 실패",
        )

    try:
        domestic = await get_cash_balance(
            app_key=app_key,
            app_secret=app_secret,
            account_no=acct.account_no,
            account_product_code=acct.acnt_prdt_cd,
            is_overseas=False,
            is_paper_trading=acct.is_paper_trading,
        )
    except RuntimeError as e:
        logger.warning("Domestic balance failed for KIS account %s: %s", acct.id, e)
        return CashSummaryAccount(
            kis_account_id=acct.id,
            label=acct.label,
            error=str(e),
        )

    # 해외 보유종목이 있으면 외화예수금/USD 환산까지 합산. 없으면 국내만.
    try:
        overseas_holdings, overseas_summary = await fetch_overseas_account_holdings(
            app_key, app_secret, acct.account_no, acct.acnt_prdt_cd
        )
    except Exception as e:
        logger.warning(
            "Overseas holdings lookup failed for account %s — domestic-only: %s",
            acct.id,
            e,
        )
        overseas_holdings = []
        overseas_summary = {}

    if overseas_holdings:
        try:
            exchange_rate = await get_exchange_rate(app_key, app_secret)
        except Exception as e:
            logger.warning(
                "Exchange rate lookup failed for account %s — using fallback 1450: %s",
                acct.id,
                e,
            )
            exchange_rate = 1450.0
        rate = Decimal(str(exchange_rate))

        ovrs_eval_usd = Decimal(str(overseas_summary.get("frcr_evlu_pfls_amt", 0) or 0))
        if ovrs_eval_usd == 0:
            ovrs_eval_usd = sum(
                h.quantity * h.avg_price for h in overseas_holdings
            )
        ovrs_pnl_usd = Decimal(str(overseas_summary.get("ovrs_tot_pfls", 0) or 0))
        ovrs_eval_krw = Decimal(int(ovrs_eval_usd * rate))
        ovrs_pnl_krw = Decimal(int(ovrs_pnl_usd * rate))

        dom_stock_eval = domestic.total_evaluation - domestic.total_cash
        combined_stock_eval = dom_stock_eval + ovrs_eval_krw

        # USD 외화예수금 — CTRP6504R 실패는 비치명적, KRW only 로 fallback.
        usd_cash = _ZERO
        usd_rate = rate
        try:
            ovrs_present = await get_overseas_present_balance(
                app_key, app_secret, acct.account_no, acct.acnt_prdt_cd
            )
            usd_cash = ovrs_present.usd_cash
            if ovrs_present.usd_krw_rate > 0:
                usd_rate = ovrs_present.usd_krw_rate
        except RuntimeError as e:
            logger.warning(
                "USD cash lookup failed for account %s — KRW-only: %s", acct.id, e
            )

        usd_cash_krw = Decimal(int(usd_cash * usd_rate))

        result = CashSummaryAccount(
            kis_account_id=acct.id,
            label=acct.label,
            total_cash=domestic.total_cash + usd_cash_krw,
            available_cash=domestic.available_cash + usd_cash_krw,
            total_evaluation=combined_stock_eval,
            total_profit_loss=domestic.total_profit_loss + ovrs_pnl_krw,
            foreign_cash=usd_cash if usd_cash > _ZERO else None,
            usd_krw_rate=usd_rate,
        )
    else:
        # 국내 전용: total_evaluation 에는 cash 가 포함돼 있어 분리한다
        # (프론트엔드는 cash + eval 합산을 별도 표시).
        result = CashSummaryAccount(
            kis_account_id=acct.id,
            label=acct.label,
            total_cash=domestic.total_cash,
            available_cash=domestic.available_cash,
            total_evaluation=domestic.total_evaluation - domestic.total_cash,
            total_profit_loss=domestic.total_profit_loss,
            foreign_cash=domestic.foreign_cash,
            usd_krw_rate=domestic.usd_krw_rate,
        )

    await _cache.setex(cache_key, ACCOUNT_CACHE_TTL, _serialize_account(result))
    return result


async def aggregate_cash_balance_for_user(
    db: AsyncSession, user: User
) -> CashSummaryResponse:
    """사용자의 모든 KIS 계좌 예수금/평가금액을 병렬 조회 후 합산.

    합산 응답 자체도 사용자 단위로 30초 캐시한다. 주문 placement/취소/체결
    시 `cash_summary:user:{user_id}` 를 invalidate 하면 즉시 반영된다.
    """
    cache_key = USER_SUMMARY_CACHE_PREFIX.format(user_id=user.id)
    cached = await _cache.get(cache_key)
    if cached:
        try:
            data = json.loads(cached)
            for field in (
                "total_cash",
                "available_cash",
                "total_evaluation",
                "total_profit_loss",
            ):
                data[field] = Decimal(data[field])
            accounts = [
                _deserialize_account(json.dumps(a)) for a in data.get("accounts", [])
            ]
            data["accounts"] = accounts
            return CashSummaryResponse(**data)
        except (ValueError, KeyError) as e:
            logger.warning("Stale/invalid cash summary cache for user %s: %s", user.id, e)

    accts_result = await db.execute(
        select(KisAccount).where(KisAccount.user_id == user.id)
    )
    accts = list(accts_result.scalars().all())

    if not accts:
        return CashSummaryResponse(
            total_cash=_ZERO,
            available_cash=_ZERO,
            total_evaluation=_ZERO,
            total_profit_loss=_ZERO,
            kis_connected=False,
            accounts=[],
            has_errors=False,
        )

    results = await asyncio.gather(
        *[fetch_cash_balance_for_account(a) for a in accts],
        return_exceptions=True,
    )

    accounts: list[CashSummaryAccount] = []
    total_cash = _ZERO
    available_cash = _ZERO
    total_evaluation = _ZERO
    total_profit_loss = _ZERO
    has_errors = False

    for acct, r in zip(accts, results):
        if isinstance(r, BaseException):
            logger.warning(
                "Unexpected error aggregating account %s: %s", acct.id, r
            )
            accounts.append(
                CashSummaryAccount(
                    kis_account_id=acct.id, label=acct.label, error=str(r)
                )
            )
            has_errors = True
            continue

        accounts.append(r)
        if r.error:
            has_errors = True
            continue

        if r.total_cash is not None:
            total_cash += r.total_cash
        if r.available_cash is not None:
            available_cash += r.available_cash
        if r.total_evaluation is not None:
            total_evaluation += r.total_evaluation
        if r.total_profit_loss is not None:
            total_profit_loss += r.total_profit_loss

    response = CashSummaryResponse(
        total_cash=total_cash,
        available_cash=available_cash,
        total_evaluation=total_evaluation,
        total_profit_loss=total_profit_loss,
        kis_connected=True,
        accounts=accounts,
        has_errors=has_errors,
    )

    # 부분 실패 응답도 30초 캐시 — 폭주 방지. 무효화는 주문 시점에 발생.
    payload = response.model_dump()
    payload = {
        k: (str(v) if isinstance(v, Decimal) else v) for k, v in payload.items()
    }
    payload["accounts"] = [
        {
            kk: (str(vv) if isinstance(vv, Decimal) else vv)
            for kk, vv in a.model_dump().items()
        }
        for a in accounts
    ]
    await _cache.setex(cache_key, USER_SUMMARY_CACHE_TTL, json.dumps(payload))

    return response


async def invalidate_user_cash_summary(user_id: int) -> None:
    """주문/체결/취소 시 사용자 단위 cash summary 캐시 무효화."""
    await _cache.delete(USER_SUMMARY_CACHE_PREFIX.format(user_id=user_id))


async def invalidate_account_cash_balance(account_id: int) -> None:
    """KIS 계좌 단위 cash balance 캐시 무효화."""
    await _cache.delete(ACCOUNT_CACHE_PREFIX.format(account_id=account_id))
