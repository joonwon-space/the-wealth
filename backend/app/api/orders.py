"""주문 API 라우터.

엔드포인트:
  POST   /portfolios/{id}/orders              - 매수/매도 주문 실행
  GET    /portfolios/{id}/orders/orderable    - 주문 가능 수량/금액 조회
  GET    /portfolios/{id}/orders/pending      - 미체결 주문 목록
  DELETE /portfolios/{id}/orders/{order_no}   - 주문 취소
  GET    /portfolios/{id}/cash-balance        - 예수금 및 총 평가금액
"""

import re
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.encryption import decrypt
from app.core.logging import get_logger
from app.core.redis_cache import RedisCache
from app.core.config import settings
from app.db.session import get_db
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.order import Order
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.order import (
    CashBalanceResponse,
    OrderRequest,
    OrderResult,
    OrderableInfoResponse,
    PendingOrderResponse,
)
from app.services.kis_account import fetch_overseas_account_holdings
from app.services.kis_balance import CashBalance, get_cash_balance
from app.services.kis_price import get_exchange_rate
from app.services.kis_order import (
    cancel_order,
    get_orderable_quantity,
    get_pending_orders,
    is_market_open,
    place_domestic_order,
    place_overseas_order,
)

router = APIRouter(tags=["orders"])
logger = get_logger(__name__)

_cache = RedisCache(settings.REDIS_URL)

_CASH_BALANCE_CACHE_PREFIX = "cash_balance:{portfolio_id}"
_CASH_BALANCE_CACHE_TTL = 30  # seconds

# 국내 티커: 숫자+영문 혼합 6자리
_DOMESTIC_TICKER_RE = re.compile(r"^[0-9A-Z]{6}$")


def _is_domestic(ticker: str) -> bool:
    return bool(_DOMESTIC_TICKER_RE.match(ticker))


async def _get_portfolio_with_kis(
    portfolio_id: int,
    current_user: User,
    db: AsyncSession,
) -> tuple[Portfolio, KisAccount, str, str]:
    """포트폴리오와 KIS 계좌 정보를 조회하고 자격증명을 복호화 반환.

    Returns:
        (portfolio, kis_account, app_key, app_secret)
    """
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없습니다")

    if not portfolio.kis_account_id:
        raise HTTPException(
            status_code=400, detail="KIS 계좌가 연결되지 않은 포트폴리오입니다"
        )

    acct = await db.get(KisAccount, portfolio.kis_account_id)
    if not acct:
        raise HTTPException(status_code=404, detail="KIS 계좌를 찾을 수 없습니다")

    try:
        app_key = decrypt(acct.app_key_enc)
        app_secret = decrypt(acct.app_secret_enc)
    except Exception as e:
        logger.warning("Failed to decrypt KIS credentials: %s", e)
        raise HTTPException(status_code=500, detail="KIS 인증 정보 복호화 실패")

    return portfolio, acct, app_key, app_secret


@router.post("/portfolios/{portfolio_id}/orders", response_model=OrderResult)
async def place_order(
    portfolio_id: int,
    body: OrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Order:
    """매수/매도 주문 실행.

    - KIS API 호출 후 orders 테이블에 기록
    - 성공 시 transactions 및 holdings 자동 업데이트
    - 장외 시간 경고 (주문 자체는 허용)
    """
    portfolio, acct, app_key, app_secret = await _get_portfolio_with_kis(
        portfolio_id, current_user, db
    )

    if not is_market_open():
        logger.info(
            "Order placed outside market hours: portfolio_id=%s ticker=%s",
            portfolio_id,
            body.ticker,
        )

    is_overseas = not _is_domestic(body.ticker)

    # SELL 전 보유 수량 검증
    if body.order_type == "SELL":
        result = await db.execute(
            select(Holding).where(
                Holding.portfolio_id == portfolio_id,
                Holding.ticker == body.ticker,
            )
        )
        holding = result.scalar_one_or_none()
        if holding is None or holding.quantity < body.quantity:
            available = holding.quantity if holding else Decimal("0")
            raise HTTPException(
                status_code=400,
                detail=f"보유 수량 부족: 보유 {available}주, 매도 요청 {body.quantity}주",
            )

    # Execute order via KIS API
    try:
        if is_overseas:
            exchange_code = body.exchange_code or "NASD"
            order_result = await place_overseas_order(
                app_key=app_key,
                app_secret=app_secret,
                account_no=acct.account_no,
                account_product_code=acct.acnt_prdt_cd,
                ticker=body.ticker,
                exchange_code=exchange_code,
                order_type=body.order_type,
                quantity=body.quantity,
                price=body.price or Decimal("0"),
                order_class=body.order_class,
                is_paper_trading=acct.is_paper_trading,
                portfolio_id=portfolio_id,
                user_id=current_user.id,
            )
        else:
            order_result = await place_domestic_order(
                app_key=app_key,
                app_secret=app_secret,
                account_no=acct.account_no,
                account_product_code=acct.acnt_prdt_cd,
                ticker=body.ticker,
                order_type=body.order_type,
                quantity=body.quantity,
                price=body.price or Decimal("0"),
                order_class=body.order_class,
                account_type=acct.account_type,
                is_paper_trading=acct.is_paper_trading,
                portfolio_id=portfolio_id,
                user_id=current_user.id,
            )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Record order in DB
    # 주문 실패 시 KIS 오류 메시지를 memo에 저장 (사용자 메모보다 우선)
    effective_memo = (
        order_result.message
        if order_result.status == "failed" and order_result.message
        else body.memo
    )
    db_order = Order(
        portfolio_id=portfolio_id,
        kis_account_id=acct.id,
        ticker=body.ticker,
        name=body.name,
        order_type=body.order_type,
        order_class=body.order_class,
        quantity=Decimal(body.quantity),
        price=body.price,
        order_no=order_result.order_no or None,
        status=order_result.status,
        memo=effective_memo,
    )
    db.add(db_order)

    # If order was placed successfully (pending), create transaction record
    if order_result.status == "pending" and order_result.order_no:
        transaction = Transaction(
            portfolio_id=portfolio_id,
            ticker=body.ticker,
            type=body.order_type,
            quantity=Decimal(body.quantity),
            price=body.price or Decimal("0"),
            memo=body.memo,
            order_no=order_result.order_no,
            order_source="kis",
        )
        db.add(transaction)

        # Update holdings
        await _update_holdings(
            db=db,
            portfolio_id=portfolio_id,
            ticker=body.ticker,
            name=body.name or body.ticker,
            order_type=body.order_type,
            quantity=Decimal(body.quantity),
            price=body.price or Decimal("0"),
        )

    await db.commit()
    await db.refresh(db_order)

    # Invalidate cash balance cache
    await _cache.delete(_CASH_BALANCE_CACHE_PREFIX.format(portfolio_id=portfolio_id))

    return db_order


async def _update_holdings(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    name: str,
    order_type: str,
    quantity: Decimal,
    price: Decimal,
) -> None:
    """매수/매도에 따라 holdings 테이블 업데이트."""
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
            # Recalculate weighted average price
            total_qty = holding.quantity + quantity
            if total_qty > 0:
                new_avg = (holding.quantity * holding.avg_price + quantity * price) / total_qty
            else:
                new_avg = price
            holding.quantity = total_qty
            holding.avg_price = new_avg
    elif order_type == "SELL":
        if holding is None:
            logger.warning(
                "SELL order processed but no local holding found: portfolio_id=%s ticker=%s",
                portfolio_id,
                ticker,
            )
            return
        new_qty = holding.quantity - quantity
        if new_qty <= 0:
            await db.delete(holding)
        else:
            holding.quantity = new_qty


@router.get("/portfolios/{portfolio_id}/orders/orderable", response_model=OrderableInfoResponse)
async def get_orderable(
    portfolio_id: int,
    ticker: str = Query(..., min_length=1, max_length=20),
    price: int = Query(0, ge=0),
    order_type: str = Query("BUY"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderableInfoResponse:
    """주문 가능 수량/금액 조회."""
    _portfolio, acct, app_key, app_secret = await _get_portfolio_with_kis(
        portfolio_id, current_user, db
    )

    try:
        info = await get_orderable_quantity(
            app_key=app_key,
            app_secret=app_secret,
            account_no=acct.account_no,
            account_product_code=acct.acnt_prdt_cd,
            ticker=ticker,
            price=price,
            order_type=order_type,
            is_paper_trading=acct.is_paper_trading,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return OrderableInfoResponse(
        orderable_quantity=info.orderable_quantity,
        orderable_amount=info.orderable_amount,
        current_price=info.current_price,
        currency=info.currency,
    )


@router.get("/portfolios/{portfolio_id}/orders/pending", response_model=list[PendingOrderResponse])
async def list_pending_orders(
    portfolio_id: int,
    is_overseas: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PendingOrderResponse]:
    """미체결 주문 목록 조회."""
    _portfolio, acct, app_key, app_secret = await _get_portfolio_with_kis(
        portfolio_id, current_user, db
    )

    try:
        pending = await get_pending_orders(
            app_key=app_key,
            app_secret=app_secret,
            account_no=acct.account_no,
            account_product_code=acct.acnt_prdt_cd,
            is_overseas=is_overseas,
            is_paper_trading=acct.is_paper_trading,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return [
        PendingOrderResponse(
            order_no=o.order_no,
            ticker=o.ticker,
            name=o.name,
            order_type=o.order_type,
            order_class=o.order_class,
            quantity=o.quantity,
            price=o.price,
            filled_quantity=o.filled_quantity,
            remaining_quantity=o.remaining_quantity,
            order_time=o.order_time,
        )
        for o in pending
    ]


@router.delete("/portfolios/{portfolio_id}/orders/{order_no}", status_code=204)
async def cancel_order_endpoint(
    portfolio_id: int,
    order_no: str,
    ticker: str = Query(...),
    quantity: int = Query(..., gt=0),
    price: int = Query(0, ge=0),
    is_overseas: bool = Query(False),
    exchange_code: str = Query(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """주문 취소."""
    _portfolio, acct, app_key, app_secret = await _get_portfolio_with_kis(
        portfolio_id, current_user, db
    )

    try:
        await cancel_order(
            app_key=app_key,
            app_secret=app_secret,
            account_no=acct.account_no,
            account_product_code=acct.acnt_prdt_cd,
            order_no=order_no,
            ticker=ticker,
            quantity=quantity,
            price=price,
            is_overseas=is_overseas,
            exchange_code=exchange_code,
            is_paper_trading=acct.is_paper_trading,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Update order status in DB
    result = await db.execute(
        select(Order).where(
            Order.portfolio_id == portfolio_id,
            Order.order_no == order_no,
        )
    )
    db_order = result.scalar_one_or_none()
    if db_order:
        db_order.status = "cancelled"
        await db.commit()


@router.get("/portfolios/{portfolio_id}/cash-balance", response_model=CashBalanceResponse)
async def get_portfolio_cash_balance(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CashBalanceResponse:
    """예수금 및 총 평가금액 조회 (국내 + 해외 합산). Redis 캐시 TTL 30초."""
    cache_key = _CASH_BALANCE_CACHE_PREFIX.format(portfolio_id=portfolio_id)
    cached = await _cache.get(cache_key)
    if cached:
        import json
        data = json.loads(cached)
        return CashBalanceResponse(**data)

    _portfolio, acct, app_key, app_secret = await _get_portfolio_with_kis(
        portfolio_id, current_user, db
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
        overseas_holdings, overseas_summary = await fetch_overseas_account_holdings(
            app_key, app_secret, acct.account_no, acct.acnt_prdt_cd
        )
        if overseas_holdings:
            exchange_rate = await get_exchange_rate(app_key, app_secret)
            rate = Decimal(str(exchange_rate))
            ovrs_eval_usd = Decimal(str(overseas_summary.get("frcr_evlu_pfls_amt", 0) or 0))
            if ovrs_eval_usd == 0:
                ovrs_eval_usd = sum(h.quantity * h.avg_price for h in overseas_holdings)
            ovrs_pnl_usd = Decimal(str(overseas_summary.get("ovrs_tot_pfls", 0) or 0))
            ovrs_eval_krw = Decimal(int(ovrs_eval_usd * rate))
            ovrs_pnl_krw = Decimal(int(ovrs_pnl_usd * rate))
            # domestic.total_evaluation = deposit + domestic_stock_eval
            dom_stock_eval = domestic.total_evaluation - domestic.total_cash
            combined_stock_eval = dom_stock_eval + ovrs_eval_krw
            balance = CashBalance(
                total_cash=domestic.total_cash,
                available_cash=domestic.available_cash,
                total_evaluation=domestic.total_cash + combined_stock_eval,
                total_profit_loss=domestic.total_profit_loss + ovrs_pnl_krw,
                profit_loss_rate=domestic.profit_loss_rate,
                currency="KRW",
                usd_krw_rate=rate,
            )
        else:
            balance = domestic
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    response = CashBalanceResponse(
        total_cash=balance.total_cash,
        available_cash=balance.available_cash,
        total_evaluation=balance.total_evaluation,
        total_profit_loss=balance.total_profit_loss,
        profit_loss_rate=balance.profit_loss_rate,
        currency=balance.currency,
        foreign_cash=balance.foreign_cash,
        usd_krw_rate=balance.usd_krw_rate,
    )

    # Cache the result
    import json
    await _cache.setex(
        cache_key,
        _CASH_BALANCE_CACHE_TTL,
        json.dumps({
            k: str(v) if isinstance(v, Decimal) else v
            for k, v in response.model_dump().items()
        }),
    )

    return response
