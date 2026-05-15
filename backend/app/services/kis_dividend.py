"""KIS 배당 데이터 수집 — 국내/해외 권리(배당) 일정.

국내: TR_ID `HHKDB669102C0` (`/uapi/domestic-stock/v1/ksdinfo/dividend`)
해외: TR_ID `HHDFS78330900` (`/uapi/overseas-price/v1/quotations/rights-by-ice`)

보유 종목 ticker 단위로 순회하여 KIS 응답을 받아 `dividends` 테이블에 upsert한다.
유니크 제약 `(ticker, market, record_date, kind)` 기준 중복 방지.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.dividend import Dividend
from app.models.holding import Holding
from app.services.kis_health import get_kis_availability
from app.services.kis_price import _get_headers
from app.services.kis_rate_limiter import kis_call_slot
from app.services.kis_retry import kis_get

logger = get_logger(__name__)

_DOMESTIC_PATH = "/uapi/domestic-stock/v1/ksdinfo/dividend"
_OVERSEAS_PATH = "/uapi/overseas-price/v1/quotations/rights-by-ice"
_DOMESTIC_TR_ID = "HHKDB669102C0"
_OVERSEAS_TR_ID = "HHDFS78330900"


def _parse_date(s: Optional[str]) -> Optional[date]:
    """KIS 응답의 YYYYMMDD 또는 YYYY-MM-DD 문자열을 date로 파싱."""
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(s: Optional[str]) -> Optional[Decimal]:
    if not s:
        return None
    try:
        return Decimal(str(s).replace(",", "").strip())
    except Exception:  # pragma: no cover - defensive
        return None


def parse_domestic_dividend_row(row: dict[str, Any]) -> Optional[dict[str, Any]]:
    """국내 KIS 응답 한 row를 Dividend upsert dict로 변환. 필수 필드 없으면 None."""
    ticker = (row.get("sht_cd") or row.get("pdno") or "").strip()
    record_date = _parse_date(row.get("record_date") or row.get("record_dt"))
    amount = _parse_decimal(row.get("per_sto_divi_amt") or row.get("dvdn_amt"))
    if not ticker or record_date is None or amount is None:
        return None
    return {
        "ticker": ticker,
        "market": "KRX",
        "ex_date": _parse_date(row.get("ex_dvdn_dt")),
        "record_date": record_date,
        "payment_date": _parse_date(row.get("dvdn_pay_dt")),
        "amount": amount,
        "currency": "KRW",
        "kind": "cash",
        "source": "kis_domestic",
        "raw": row,
    }


def parse_overseas_dividend_row(row: dict[str, Any]) -> Optional[dict[str, Any]]:
    """해외 ICE 응답 row를 Dividend upsert dict로 변환."""
    ticker = (row.get("symb") or row.get("rsym") or "").strip()
    market = (row.get("excd") or row.get("exch") or "").strip() or "OVS"
    record_date = _parse_date(row.get("record_date") or row.get("rcdt"))
    amount = _parse_decimal(row.get("per_sto_divi_amt") or row.get("dvdn_amt"))
    if not ticker or record_date is None or amount is None:
        return None
    return {
        "ticker": ticker,
        "market": market,
        "ex_date": _parse_date(row.get("ex_date") or row.get("exdt")),
        "record_date": record_date,
        "payment_date": _parse_date(row.get("pay_date") or row.get("paydt")),
        "amount": amount,
        "currency": (row.get("currency") or "USD").strip().upper()[:3],
        "kind": "cash",
        "source": "kis_overseas_ice",
        "raw": row,
    }


async def _fetch_domestic_dividend_pages(
    ticker: str, app_key: str, app_secret: str, client: httpx.AsyncClient,
) -> list[dict[str, Any]]:
    """국내 배당 일정 — `tr_cont` 페이지 커서 처리."""
    rows: list[dict[str, Any]] = []
    headers_base = await _get_headers(app_key, app_secret)
    tr_cont = ""
    ctx_area_fk100 = ""
    ctx_area_nk100 = ""
    for _ in range(20):  # 안전 상한
        headers = {
            **headers_base,
            "tr_id": _DOMESTIC_TR_ID,
            "tr_cont": tr_cont,
        }
        params = {
            "CTS": "",
            "GB1": "0",  # 0=전체
            "F_DT": "",
            "T_DT": "",
            "SHT_CD": ticker,
            "HIGH_GB": "",
            "CTX_AREA_FK100": ctx_area_fk100,
            "CTX_AREA_NK100": ctx_area_nk100,
        }
        async with kis_call_slot():
            resp = await kis_get(
                client,
                f"{settings.KIS_BASE_URL}{_DOMESTIC_PATH}",
                headers=headers,
                params=params,
            )
        resp.raise_for_status()
        body = resp.json()
        chunk = body.get("output1") or body.get("output") or []
        if isinstance(chunk, list):
            rows.extend(chunk)
        next_cont = resp.headers.get("tr_cont", "")
        if next_cont not in ("F", "M"):
            break
        tr_cont = "N"
        ctx_area_fk100 = body.get("ctx_area_fk100", "") or ""
        ctx_area_nk100 = body.get("ctx_area_nk100", "") or ""
    return rows


async def _fetch_overseas_dividend(
    ticker: str, market: str, app_key: str, app_secret: str, client: httpx.AsyncClient,
) -> list[dict[str, Any]]:
    headers_base = await _get_headers(app_key, app_secret)
    headers = {**headers_base, "tr_id": _OVERSEAS_TR_ID}
    params = {
        "AUTH": "",
        "EXCD": market or "NAS",
        "SYMB": ticker,
    }
    async with kis_call_slot():
        resp = await kis_get(
            client,
            f"{settings.KIS_BASE_URL}{_OVERSEAS_PATH}",
            headers=headers,
            params=params,
        )
    resp.raise_for_status()
    body = resp.json()
    chunk = body.get("output") or body.get("output1") or []
    return chunk if isinstance(chunk, list) else []


async def upsert_dividends(
    db: AsyncSession, rows: Iterable[dict[str, Any]],
) -> int:
    """Dividend rows를 unique constraint 기준으로 upsert. 신규 insert 수 반환."""
    inserted = 0
    for row in rows:
        if row is None:
            continue
        stmt = (
            pg_insert(Dividend)
            .values(**row)
            .on_conflict_do_update(
                constraint="uq_dividends_ticker_market_record_kind",
                set_={
                    "ex_date": row.get("ex_date"),
                    "payment_date": row.get("payment_date"),
                    "amount": row["amount"],
                    "currency": row.get("currency", "KRW"),
                    "source": row.get("source", "manual"),
                    "raw": row.get("raw"),
                },
            )
        )
        result = await db.execute(stmt)
        # PostgreSQL ON CONFLICT DO UPDATE 시 rowcount는 1로 반환되지만,
        # insert/update 구분이 어렵다. 단순 카운트 용도로 사용.
        inserted += int(result.rowcount or 0)
    await db.commit()
    return inserted


async def collect_dividends_for_user_holdings(
    db: AsyncSession, app_key: str, app_secret: str,
) -> dict[str, int]:
    """모든 사용자의 보유 종목 ticker(market 별 dedup) 단위로 KIS 호출.

    KIS 가용성 플래그가 False면 즉시 종료한다.
    반환: {"domestic": N, "overseas": M, "errors": E}
    """
    if not get_kis_availability():
        logger.warning("[KisDividend] KIS unavailable — skipping dividend collection")
        return {"domestic": 0, "overseas": 0, "errors": 0}

    # 보유 중인 종목만 수집 (CSV/manual은 ticker_market 추정 어려움 → 추후)
    holdings_q = await db.execute(select(Holding.ticker).distinct())
    tickers = sorted({t[0] for t in holdings_q.all() if t[0]})

    domestic_count = 0
    overseas_count = 0
    errors = 0

    async with httpx.AsyncClient(timeout=15.0) as client:
        for ticker in tickers:
            is_domestic = ticker.isdigit() and len(ticker) == 6
            try:
                if is_domestic:
                    rows = await _fetch_domestic_dividend_pages(
                        ticker, app_key, app_secret, client
                    )
                    parsed = [parse_domestic_dividend_row(r) for r in rows]
                    inserted = await upsert_dividends(db, [p for p in parsed if p])
                    domestic_count += inserted
                else:
                    rows = await _fetch_overseas_dividend(
                        ticker, "NAS", app_key, app_secret, client
                    )
                    parsed = [parse_overseas_dividend_row(r) for r in rows]
                    inserted = await upsert_dividends(db, [p for p in parsed if p])
                    overseas_count += inserted
            except (httpx.ConnectError, httpx.TimeoutException, OSError) as exc:
                errors += 1
                logger.warning(
                    "[KisDividend] network error ticker=%s — %s", ticker, exc
                )
            except Exception as exc:  # noqa: BLE001 — collect errors, continue batch
                errors += 1
                logger.exception(
                    "[KisDividend] unexpected error ticker=%s: %s", ticker, exc
                )

    logger.info(
        "[KisDividend] collected — domestic=%d overseas=%d errors=%d",
        domestic_count, overseas_count, errors,
    )
    return {"domestic": domestic_count, "overseas": overseas_count, "errors": errors}
