"""KIS 계좌 보유 종목 vs DB holdings Reconciliation 알고리즘.

동작:
- 신규 종목 → INSERT
- 청산된 종목 → DELETE
- 수량/평균단가 변경 → UPDATE
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.holding import Holding
from app.services.kis_account import KisHolding

logger = get_logger(__name__)


async def reconcile_holdings(
    db: AsyncSession,
    portfolio_id: int,
    kis_holdings: list[KisHolding],
) -> dict[str, int]:
    """DB holdings를 KIS 실계좌 데이터에 맞게 동기화.

    Returns:
        {"inserted": N, "updated": N, "deleted": N}
    """
    result = await db.execute(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    )
    db_holdings: list[Holding] = list(result.scalars().all())

    db_map = {h.ticker: h for h in db_holdings}
    kis_map = {k.ticker: k for k in kis_holdings}

    counts = {"inserted": 0, "updated": 0, "deleted": 0}

    # INSERT: KIS에 있지만 DB에 없는 종목
    for ticker, kis in kis_map.items():
        if ticker not in db_map:
            new_holding = Holding(
                portfolio_id=portfolio_id,
                ticker=kis.ticker,
                name=kis.name,
                quantity=kis.quantity,
                avg_price=kis.avg_price,
                market=kis.market,
            )
            db.add(new_holding)
            counts["inserted"] += 1
            logger.info("Reconcile INSERT: %s (portfolio=%d)", ticker, portfolio_id)

    # UPDATE: 양쪽에 있지만 수량/단가/market 다른 종목
    for ticker, db_h in db_map.items():
        if ticker in kis_map:
            kis = kis_map[ticker]
            changed = (
                db_h.quantity != kis.quantity
                or db_h.avg_price != kis.avg_price
                or db_h.market != kis.market
            )
            if changed:
                db_h.quantity = kis.quantity
                db_h.avg_price = kis.avg_price
                db_h.market = kis.market
                counts["updated"] += 1
                logger.info("Reconcile UPDATE: %s (portfolio=%d)", ticker, portfolio_id)

    # DELETE: DB에 있지만 KIS에 없는 종목
    for ticker, db_h in db_map.items():
        if ticker not in kis_map:
            await db.delete(db_h)
            counts["deleted"] += 1
            logger.info("Reconcile DELETE: %s (portfolio=%d)", ticker, portfolio_id)

    await db.commit()
    return counts
