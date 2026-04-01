from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.encryption import decrypt
from app.db.session import get_db
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.models.user import User
from app.core.logging import get_logger
from app.core.ticker import is_domestic
import asyncio
import httpx
from app.services.kis_price import (
    fetch_usd_krw_rate,
    get_or_fetch_domestic_price,
    get_or_fetch_overseas_price,
)
from app.schemas.portfolio import (
    BulkHoldingRequest,
    BulkHoldingResult,
    HoldingCreate,
    HoldingResponse,
    HoldingUpdate,
    PortfolioCreate,
    PortfolioResponse,
    PortfolioUpdate,
    ReorderRequest,
    TransactionCreate,
    TransactionMemoUpdate,
    TransactionPage,
    TransactionResponse,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])
logger = get_logger(__name__)


def _assert_portfolio_owner(portfolio: Portfolio, user: User) -> None:
    if portfolio.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )


def _assert_holding_owner(holding: Holding, portfolio: Portfolio, user: User) -> None:
    if portfolio.user_id != user.id or holding.portfolio_id != portfolio.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )


@router.get("", response_model=list[PortfolioResponse])
async def list_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    # Single query with LEFT JOIN + GROUP BY instead of N+1

    stmt = (
        select(
            Portfolio,
            KisAccount.label,
            func.count(Holding.id).label("holdings_count"),
            func.coalesce(
                func.sum(Holding.quantity * Holding.avg_price), Decimal("0")
            ).label("total_invested"),
        )
        .outerjoin(KisAccount, KisAccount.id == Portfolio.kis_account_id)
        .outerjoin(Holding, Holding.portfolio_id == Portfolio.id)
        .where(Portfolio.user_id == current_user.id)
        .group_by(Portfolio.id, KisAccount.label)
        .order_by(Portfolio.display_order.asc(), Portfolio.created_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": p.id,
            "user_id": p.user_id,
            "name": kis_label if kis_label else p.name,
            "currency": p.currency,
            "display_order": p.display_order,
            "created_at": p.created_at,
            "holdings_count": count,
            "total_invested": invested,
            "kis_account_id": p.kis_account_id,
            "target_value": p.target_value,
        }
        for p, kis_label, count, invested in rows
    ]


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    body: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Portfolio:
    # 기존 포트폴리오 최대 display_order + 1 로 새 포트폴리오 순서 설정
    max_order_result = await db.execute(
        select(func.max(Portfolio.display_order)).where(Portfolio.user_id == current_user.id)
    )
    max_order = max_order_result.scalar() or -1
    portfolio = Portfolio(
        user_id=current_user.id,
        name=body.name,
        currency=body.currency,
        display_order=max_order + 1,
    )
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return portfolio


@router.patch("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_portfolios(
    body: ReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """포트폴리오 순서 일괄 업데이트. IDOR 방지: 본인 포트폴리오만 허용."""
    ids = [item.id for item in body.items]
    result = await db.execute(
        select(Portfolio).where(Portfolio.id.in_(ids), Portfolio.user_id == current_user.id)
    )
    owned = {p.id for p in result.scalars().all()}
    if owned != set(ids):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    for item in body.items:
        await db.execute(
            Portfolio.__table__.update()
            .where(Portfolio.id == item.id)
            .values(display_order=item.display_order)
        )
    await db.commit()


@router.patch("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: int,
    body: PortfolioUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)
    if body.name is not None:
        portfolio.name = body.name
    if body.currency is not None:
        portfolio.currency = body.currency
    if "target_value" in body.model_fields_set:
        portfolio.target_value = body.target_value

    # Sync KIS account label if linked and name changed
    if body.name is not None and portfolio.kis_account_id:
        acct = await db.get(KisAccount, portfolio.kis_account_id)
        if acct:
            acct.label = body.name

    await db.commit()
    await db.refresh(portfolio)

    stats = await db.execute(
        select(
            func.count(Holding.id),
            func.coalesce(func.sum(Holding.quantity * Holding.avg_price), Decimal("0")),
        ).where(Holding.portfolio_id == portfolio.id)
    )
    count, invested = stats.one()
    return {
        "id": portfolio.id,
        "user_id": portfolio.user_id,
        "name": portfolio.name,
        "currency": portfolio.currency,
        "display_order": portfolio.display_order,
        "created_at": portfolio.created_at,
        "holdings_count": count,
        "total_invested": invested,
        "target_value": portfolio.target_value,
    }


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)
    await db.delete(portfolio)
    await db.commit()


@router.get("/{portfolio_id}/holdings", response_model=list[HoldingResponse])
async def list_holdings(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Holding]:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    result = await db.execute(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    )
    return list(result.scalars().all())


@router.get("/{portfolio_id}/holdings/with-prices")
async def list_holdings_with_prices(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Holdings with current prices and P&L from the linked KIS account."""
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    result = await db.execute(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    )
    holdings = list(result.scalars().all())
    if not holdings:
        return []

    # ticker → market code 매핑 (해외주식만)
    _MARKET_MAP = {
        "NASD": "NAS", "NYSE": "NYS", "AMEX": "AMS",
        "SEHK": "HKS", "TKSE": "TSE", "SHAA": "SHS",
        "SZAA": "SZS", "HASE": "HNX", "VNSE": "HSX",
    }
    overseas_holdings = [h for h in holdings if not is_domestic(h.ticker)]
    ticker_to_market = {
        h.ticker: _MARKET_MAP.get(h.market or "", h.market or "NAS")
        for h in overseas_holdings
    }

    prices: dict[str, Decimal | None] = {}
    exchange_rate = Decimal("1450")

    if portfolio.kis_account_id:
        acct = await db.get(KisAccount, portfolio.kis_account_id)
        if acct:
            try:
                app_key = decrypt(acct.app_key_enc)
                app_secret = decrypt(acct.app_secret_enc)
                domestic_tickers = list({h.ticker for h in holdings if is_domestic(h.ticker)})
                overseas_tickers = list({h.ticker for h in overseas_holdings})
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 국내주식 현재가 (캐시 우선)
                    domestic_tasks = [
                        get_or_fetch_domestic_price(t, app_key, app_secret, client)
                        for t in domestic_tickers
                    ]
                    # 해외주식 현재가 (캐시 우선, current 가격만)
                    overseas_tasks = [
                        get_or_fetch_overseas_price(t, ticker_to_market[t], app_key, app_secret, client)
                        for t in overseas_tickers
                    ]
                    fx_task = (
                        fetch_usd_krw_rate(app_key, app_secret, client)
                        if overseas_holdings else asyncio.sleep(0, result=Decimal("1450"))
                    )
                    *all_prices, fx = await asyncio.gather(
                        *domestic_tasks, *overseas_tasks, fx_task, return_exceptions=True
                    )

                domestic_results = all_prices[: len(domestic_tickers)]
                overseas_results = all_prices[len(domestic_tickers):]

                for ticker, price in zip(domestic_tickers, domestic_results):
                    if isinstance(price, Decimal) and price > 0:
                        prices[ticker] = price
                if isinstance(fx, Decimal):
                    exchange_rate = fx
                for ticker, price in zip(overseas_tickers, overseas_results):
                    if isinstance(price, Decimal) and price > 0:
                        prices[ticker] = price

            except Exception as e:
                logger.warning(
                    "Failed to fetch prices for portfolio %d: %s", portfolio_id, e
                )

    items = []
    for h in holdings:
        is_overseas = not is_domestic(h.ticker)
        cp = prices.get(h.ticker)
        invested = h.quantity * h.avg_price

        if is_overseas:
            invested_krw = invested * exchange_rate
            mv_usd = h.quantity * cp if cp is not None else None
            mv_krw = mv_usd * exchange_rate if mv_usd is not None else None
            pnl_krw = mv_krw - invested_krw if mv_krw is not None else None
            pnl_rate = (pnl_krw / invested_krw * 100) if pnl_krw is not None and invested_krw else None
            items.append({
                "id": h.id,
                "ticker": h.ticker,
                "name": h.name,
                "quantity": str(h.quantity),
                "avg_price": str(h.avg_price),
                "current_price": str(cp) if cp is not None else None,
                "market_value": str(mv_usd) if mv_usd is not None else None,
                "market_value_krw": str(mv_krw) if mv_krw is not None else None,
                "pnl_amount": str(pnl_krw) if pnl_krw is not None else None,
                "pnl_rate": str(pnl_rate) if pnl_rate is not None else None,
                "exchange_rate": str(exchange_rate),
                "currency": "USD",
            })
        else:
            mv = h.quantity * cp if cp is not None else None
            pnl = mv - invested if mv is not None else None
            pnl_rate = (pnl / invested * 100) if pnl is not None and invested else None
            items.append({
                "id": h.id,
                "ticker": h.ticker,
                "name": h.name,
                "quantity": str(h.quantity),
                "avg_price": str(h.avg_price),
                "current_price": str(cp) if cp is not None else None,
                "market_value": str(mv) if mv is not None else None,
                "market_value_krw": str(mv) if mv is not None else None,
                "pnl_amount": str(pnl) if pnl is not None else None,
                "pnl_rate": str(pnl_rate) if pnl_rate is not None else None,
                "exchange_rate": None,
                "currency": "KRW",
            })
    return items


@router.post(
    "/{portfolio_id}/holdings",
    response_model=HoldingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_holding(
    portfolio_id: int,
    body: HoldingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Holding:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    holding = Holding(
        portfolio_id=portfolio_id,
        ticker=body.ticker,
        name=body.name,
        quantity=body.quantity,
        avg_price=body.avg_price,
        market=body.market,
    )
    db.add(holding)
    await db.commit()
    await db.refresh(holding)
    return holding


@router.post(
    "/{portfolio_id}/holdings/bulk",
    response_model=BulkHoldingResult,
    status_code=status.HTTP_200_OK,
)
async def bulk_add_holdings(
    portfolio_id: int,
    body: BulkHoldingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BulkHoldingResult:
    """보유 종목 일괄 등록/업데이트.

    - 신규 ticker: 새 Holding 생성
    - 기존 ticker: 수량 합산 + 가중평균 평단가 업데이트
    - 최대 100건; 유효성 오류 항목은 건너뛰고 errors 목록에 추가
    """
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    # 기존 보유 종목 조회 (ticker → Holding 맵)
    existing_result = await db.execute(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    )
    existing_map: dict[str, Holding] = {h.ticker: h for h in existing_result.scalars().all()}

    created = 0
    updated = 0
    errors: list[str] = []

    for item in body.items:
        try:
            if item.ticker in existing_map:
                # upsert: 가중평균 평단가 계산
                existing = existing_map[item.ticker]
                old_qty = existing.quantity
                old_price = existing.avg_price
                new_qty = item.quantity
                new_price = item.avg_price
                total_qty = old_qty + new_qty
                weighted_avg = (old_qty * old_price + new_qty * new_price) / total_qty
                existing.quantity = total_qty
                existing.avg_price = weighted_avg
                updated += 1
            else:
                holding = Holding(
                    portfolio_id=portfolio_id,
                    ticker=item.ticker,
                    name=item.name,
                    quantity=item.quantity,
                    avg_price=item.avg_price,
                    market=item.market,
                )
                db.add(holding)
                existing_map[item.ticker] = holding
                created += 1
        except Exception as exc:
            errors.append(f"{item.ticker}: {exc}")

    await db.commit()
    logger.info(
        "Bulk holdings upsert: portfolio=%d created=%d updated=%d errors=%d",
        portfolio_id, created, updated, len(errors),
    )
    return BulkHoldingResult(created=created, updated=updated, errors=errors)


@router.patch("/holdings/{holding_id}", response_model=HoldingResponse)
async def update_holding(
    holding_id: int,
    body: HoldingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Holding:
    holding = await db.get(Holding, holding_id)
    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found"
        )
    portfolio = await db.get(Portfolio, holding.portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_holding_owner(holding, portfolio, current_user)

    if body.quantity is not None:
        holding.quantity = body.quantity
    if body.avg_price is not None:
        holding.avg_price = body.avg_price
    await db.commit()
    await db.refresh(holding)
    return holding


@router.delete("/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holding(
    holding_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    holding = await db.get(Holding, holding_id)
    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found"
        )
    portfolio = await db.get(Portfolio, holding.portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_holding_owner(holding, portfolio, current_user)

    await db.delete(holding)
    await db.commit()


@router.get("/{portfolio_id}/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    portfolio_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Transaction]:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.deleted_at.is_(None),
        )
        .order_by(Transaction.traded_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{portfolio_id}/transactions/paginated", response_model=TransactionPage)
async def list_transactions_paginated(
    portfolio_id: int,
    cursor: int = Query(default=0, ge=0, description="마지막으로 조회한 transaction ID (0이면 처음부터)"),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """커서 기반 트랜잭션 페이지네이션.

    cursor: 이전 페이지의 마지막 트랜잭션 ID (0이면 첫 페이지).
    Returns: { items, next_cursor, has_more }
    """
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    query = (
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.deleted_at.is_(None),
        )
        .order_by(Transaction.traded_at.desc(), Transaction.id.desc())
    )
    if cursor > 0:
        # Fetch the reference transaction to get its traded_at for proper cursor
        ref_txn = await db.get(Transaction, cursor)
        if ref_txn and ref_txn.portfolio_id == portfolio_id:
            query = query.where(
                (Transaction.traded_at < ref_txn.traded_at)
                | (
                    (Transaction.traded_at == ref_txn.traded_at)
                    & (Transaction.id < cursor)
                )
            )

    # Fetch limit + 1 to determine has_more
    result = await db.execute(query.limit(limit + 1))
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = items[-1].id if has_more else None

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }


@router.post(
    "/{portfolio_id}/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    portfolio_id: int,
    body: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Transaction:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    txn = Transaction(
        portfolio_id=portfolio_id,
        ticker=body.ticker,
        type=body.type,
        quantity=body.quantity,
        price=body.price,
    )
    if body.traded_at:
        txn.traded_at = body.traded_at
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return txn


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    txn = await db.get(Transaction, transaction_id)
    if not txn or txn.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )
    portfolio = await db.get(Portfolio, txn.portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)
    # Soft delete: set deleted_at instead of hard delete
    txn.deleted_at = datetime.now(timezone.utc)
    await db.commit()


@router.patch(
    "/{portfolio_id}/transactions/{transaction_id}",
    response_model=TransactionResponse,
)
async def update_transaction_memo(
    portfolio_id: int,
    transaction_id: int,
    body: TransactionMemoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Transaction:
    """거래 메모 업데이트 (인라인 편집)."""
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    txn = await db.get(Transaction, transaction_id)
    if not txn or txn.deleted_at is not None or txn.portfolio_id != portfolio_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )

    txn.memo = body.memo
    if body.tags is not None:
        txn.tags = body.tags
    await db.commit()
    await db.refresh(txn)
    return txn


@router.get("/{portfolio_id}/kis-transactions")
async def list_kis_transactions(
    portfolio_id: int,
    from_date: str = Query(..., pattern=r"^\d{8}$", description="YYYYMMDD"),
    to_date: str = Query(..., pattern=r"^\d{8}$", description="YYYYMMDD"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """KIS API에서 체결 내역 조회 (국내 + 해외). KIS 계정 연결 필요."""
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    _assert_portfolio_owner(portfolio, current_user)

    if not portfolio.kis_account_id:
        return []

    acct = await db.get(KisAccount, portfolio.kis_account_id)
    if not acct:
        return []

    from app.services.kis_transaction import fetch_domestic_transactions, fetch_overseas_transactions

    try:
        app_key = decrypt(acct.app_key_enc)
        app_secret = decrypt(acct.app_secret_enc)
        async with httpx.AsyncClient(timeout=15.0) as client:
            domestic, overseas = await asyncio.gather(
                fetch_domestic_transactions(
                    app_key, app_secret, acct.account_no, acct.acnt_prdt_cd,
                    from_date, to_date, client,
                ),
                fetch_overseas_transactions(
                    app_key, app_secret, acct.account_no, acct.acnt_prdt_cd,
                    from_date, to_date, client,
                ),
                return_exceptions=True,
            )
        results: list[dict] = []
        if isinstance(domestic, list):
            results.extend(domestic)
        if isinstance(overseas, list):
            results.extend(overseas)
        results.sort(key=lambda x: x.get("traded_at", ""), reverse=True)
        return results
    except Exception as e:
        logger.warning("KIS transaction fetch failed for portfolio %d: %s", portfolio_id, e)
        return []

