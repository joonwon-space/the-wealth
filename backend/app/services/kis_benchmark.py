"""KIS OpenAPI 벤치마크 지수 수집 서비스.

KOSPI200과 S&P500의 현재 지수 스냅샷을 KIS API에서 조회하여
index_snapshots 테이블에 upsert합니다.

TR_IDs:
- KOSPI200: FHKUP03500100 (국내지수 현재가)
- S&P500:   FHKST03030100 (해외지수 현재가)
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.index_snapshot import IndexSnapshot
from app.services.kis_token import get_kis_access_token

logger = get_logger(__name__)

_KST = timezone(timedelta(hours=9))

# Index definitions: (display_code, tr_id, market_type)
_INDICES = [
    ("KOSPI200", "FHKUP03500100", "domestic"),
    ("SP500", "FHKST03030100", "overseas"),
]


@dataclass(frozen=True)
class IndexSnapshotData:
    """KIS API에서 조회한 지수 스냅샷."""

    index_code: str
    timestamp: datetime
    close_price: Decimal
    change_pct: Optional[Decimal]


async def _fetch_domestic_index(
    app_key: str,
    app_secret: str,
    index_code: str,
    tr_id: str,
) -> Optional[IndexSnapshotData]:
    """국내 지수 현재가 조회 (FHKUP03500100).

    시장 구분: 0001=KOSPI, 0002=KOSDAQ, 0003=KOSPI200
    """
    token = await get_kis_access_token(app_key, app_secret)
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "Content-Type": "application/json; charset=utf-8",
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "U",
        "FID_INPUT_ISCD": "0003",  # KOSPI200
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-index-price",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        rt_cd = data.get("rt_cd")
        if rt_cd != "0":
            msg = data.get("msg1", "Unknown KIS API error")
            logger.warning("Domestic index fetch failed: index=%s msg=%s", index_code, msg)
            return None

        output = data.get("output", {})
        close_str = output.get("bstp_nmix_prpr", "") or output.get("stck_prpr", "")
        change_str = output.get("bstp_nmix_prdy_ctrt", "") or output.get("prdy_ctrt", "")

        if not close_str:
            logger.warning("No price data for index: %s", index_code)
            return None

        return IndexSnapshotData(
            index_code=index_code,
            timestamp=datetime.now(_KST),
            close_price=Decimal(close_str.replace(",", "")),
            change_pct=Decimal(change_str) if change_str else None,
        )

    except Exception as e:
        logger.warning("_fetch_domestic_index error: index=%s error=%s", index_code, e)
        return None


async def _fetch_overseas_index(
    app_key: str,
    app_secret: str,
    index_code: str,
    tr_id: str,
) -> Optional[IndexSnapshotData]:
    """해외 지수 현재가 조회 (FHKST03030100).

    거래소: N=NYSE, A=AMEX, Q=NASDAQ, S=S&P500
    종목코드: .SPX = S&P500
    """
    token = await get_kis_access_token(app_key, app_secret)
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "Content-Type": "application/json; charset=utf-8",
    }
    params = {
        "AUTH": "",
        "EXCD": "S",  # S&P500 market
        "SYMB": ".SPX",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.KIS_BASE_URL}/uapi/overseas-price/v1/quotations/price",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        rt_cd = data.get("rt_cd")
        if rt_cd != "0":
            msg = data.get("msg1", "Unknown KIS API error")
            logger.warning("Overseas index fetch failed: index=%s msg=%s", index_code, msg)
            return None

        output = data.get("output", {})
        close_str = output.get("last", "") or output.get("stck_prpr", "")
        change_str = output.get("rate", "") or output.get("prdy_ctrt", "")

        if not close_str:
            logger.warning("No price data for overseas index: %s", index_code)
            return None

        return IndexSnapshotData(
            index_code=index_code,
            timestamp=datetime.now(_KST),
            close_price=Decimal(close_str.replace(",", "")),
            change_pct=Decimal(change_str) if change_str else None,
        )

    except Exception as e:
        logger.warning("_fetch_overseas_index error: index=%s error=%s", index_code, e)
        return None


async def _upsert_snapshot_with_session(
    db: "AsyncSession", snapshot: IndexSnapshotData
) -> None:
    """index_snapshots 테이블에 upsert — 외부 세션을 받아 실행.

    커밋은 호출자 책임이다.  이 함수는 세션을 생성하거나 닫지 않는다.
    """
    stmt = (
        pg_insert(IndexSnapshot)
        .values(
            index_code=snapshot.index_code,
            timestamp=snapshot.timestamp,
            close_price=snapshot.close_price,
            change_pct=snapshot.change_pct,
        )
        .on_conflict_do_update(
            constraint="uq_index_snapshot_code_ts",
            set_={
                "close_price": snapshot.close_price,
                "change_pct": snapshot.change_pct,
            },
        )
    )
    await db.execute(stmt)


async def _upsert_snapshot(snapshot: IndexSnapshotData) -> None:
    """index_snapshots 테이블에 upsert (충돌 시 close_price/change_pct 갱신).

    스케줄러처럼 세션 없이 직접 호출되는 경우를 위한 편의 래퍼.
    내부에서 세션을 생성하고 커밋한 뒤 닫는다.
    """
    async with AsyncSessionLocal() as db:
        await _upsert_snapshot_with_session(db, snapshot)
        await db.commit()


async def collect_snapshots(app_key: str, app_secret: str) -> dict[str, bool]:
    """KOSPI200 및 S&P500 스냅샷을 수집하여 DB에 저장.

    Returns:
        dict mapping index_code to success flag.
    """
    tasks = [
        _fetch_domestic_index(app_key, app_secret, "KOSPI200", "FHKUP03500100"),
        _fetch_overseas_index(app_key, app_secret, "SP500", "FHKST03030100"),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    status: dict[str, bool] = {}
    codes = ["KOSPI200", "SP500"]

    for code, result in zip(codes, results):
        if isinstance(result, Exception):
            logger.warning("collect_snapshots: %s raised %s", code, result)
            status[code] = False
        elif result is None:
            logger.warning("collect_snapshots: %s returned no data", code)
            status[code] = False
        else:
            try:
                await _upsert_snapshot(result)
                logger.info(
                    "collect_snapshots: saved %s close=%s change_pct=%s",
                    code,
                    result.close_price,
                    result.change_pct,
                )
                status[code] = True
            except Exception as e:
                logger.warning("collect_snapshots: upsert failed for %s: %s", code, e)
                status[code] = False

    return status
