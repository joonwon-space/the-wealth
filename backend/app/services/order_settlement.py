"""미체결 주문 체결 확인 및 transaction/holding 반영 서비스.

스케줄러 또는 수동 API 호출로 실행되며, DB의 pending/partial 주문을
KIS 체결조회 API로 확인한 뒤 체결분만 transaction과 holding에 반영한다.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.holding import Holding
from app.models.order import Order
from app.models.transaction import Transaction
from app.services.kis_order import FilledOrderInfo, check_filled_orders

logger = get_logger(__name__)


async def _update_holdings_for_fill(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    name: str,
    order_type: str,
    quantity: Decimal,
    price: Decimal,
) -> None:
    """체결 확인된 주문에 대해 holdings를 업데이트한다."""
    result = await db.execute(
        select(Holding).where(
            Holding.portfolio_id == portfolio_id,
            Holding.ticker == ticker,
        )
    )
    holding = result.scalar_one_or_none()

    if order_type == "BUY":
        if holding is None:
            holding = Holding(
                portfolio_id=portfolio_id,
                ticker=ticker,
                name=name,
                quantity=quantity,
                avg_price=price,
            )
            db.add(holding)
        else:
            total_qty = holding.quantity + quantity
            if total_qty > 0:
                new_avg = (
                    holding.quantity * holding.avg_price + quantity * price
                ) / total_qty
            else:
                new_avg = price
            holding.quantity = total_qty
            holding.avg_price = new_avg
    elif order_type == "SELL":
        if holding is None:
            logger.warning(
                "SELL fill but no holding found: portfolio_id=%s ticker=%s",
                portfolio_id,
                ticker,
            )
            return
        new_qty = holding.quantity - quantity
        if new_qty <= 0:
            await db.delete(holding)
        else:
            holding.quantity = new_qty


async def settle_pending_orders(
    db: AsyncSession,
    portfolio_id: int,
    app_key: str,
    app_secret: str,
    account_no: str,
    account_product_code: str,
    is_paper_trading: bool = False,
) -> dict[str, int]:
    """포트폴리오의 pending/partial 주문을 KIS 체결조회로 확인하고 반영한다.

    Returns:
        {"settled": N, "partial": N, "unchanged": N} 처리 결과 카운트
    """
    # 1. DB에서 pending/partial 상태 주문 조회
    result = await db.execute(
        select(Order).where(
            Order.portfolio_id == portfolio_id,
            Order.status.in_(["pending", "partial"]),
        )
    )
    pending_orders = list(result.scalars().all())

    if not pending_orders:
        return {"settled": 0, "partial": 0, "unchanged": 0}

    order_nos = [o.order_no for o in pending_orders if o.order_no]
    if not order_nos:
        return {"settled": 0, "partial": 0, "unchanged": 0}

    # 2. KIS 체결 조회
    filled_infos = await check_filled_orders(
        app_key=app_key,
        app_secret=app_secret,
        account_no=account_no,
        account_product_code=account_product_code,
        order_nos=order_nos,
        is_paper_trading=is_paper_trading,
    )

    # order_no → FilledOrderInfo 매핑
    filled_map: dict[str, FilledOrderInfo] = {f.order_no: f for f in filled_infos}

    counts = {"settled": 0, "partial": 0, "unchanged": 0}

    for order in pending_orders:
        if not order.order_no or order.order_no not in filled_map:
            counts["unchanged"] += 1
            continue

        info = filled_map[order.order_no]
        prev_filled = order.filled_quantity or Decimal("0")
        new_filled = info.filled_quantity - prev_filled

        if new_filled <= 0:
            counts["unchanged"] += 1
            continue

        # 3. Order 상태 업데이트
        order.filled_quantity = info.filled_quantity
        order.filled_price = info.filled_price

        if info.is_fully_filled:
            order.status = "filled"
            counts["settled"] += 1
        else:
            order.status = "partial"
            counts["partial"] += 1

        # 4. Transaction 생성 (새로 체결된 수량만)
        transaction = Transaction(
            portfolio_id=portfolio_id,
            ticker=info.ticker,
            type=info.order_type,
            quantity=new_filled,
            price=info.filled_price,
            memo=f"KIS 체결 (주문번호: {order.order_no})",
            order_no=order.order_no,
            order_source="kis",
        )
        db.add(transaction)

        # 5. Holdings 업데이트 (새로 체결된 수량만)
        await _update_holdings_for_fill(
            db=db,
            portfolio_id=portfolio_id,
            ticker=info.ticker,
            name=order.name or info.ticker,
            order_type=info.order_type,
            quantity=new_filled,
            price=info.filled_price,
        )

        logger.info(
            "Order settled: order_no=%s ticker=%s type=%s filled=%s price=%s status=%s",
            order.order_no,
            info.ticker,
            info.order_type,
            new_filled,
            info.filled_price,
            order.status,
        )

    await db.commit()
    return counts
