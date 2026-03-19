"""데이터 무결성 헬스체크 API."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.price_snapshot import PriceSnapshot
from app.models.sync_log import SyncLog
from app.models.transaction import Transaction
from app.models.user import User

router = APIRouter(prefix="/health", tags=["health"])


def _last_n_weekdays(n: int, reference: date) -> list[date]:
    """reference 날짜 이전 n개의 평일(월~금) 반환 (reference 포함 가능)."""
    days: list[date] = []
    current = reference
    while len(days) < n:
        if current.weekday() < 5:  # 0=월 ~ 4=금
            days.append(current)
        current -= timedelta(days=1)
    return days


@router.get("/data-integrity")
async def data_integrity_check(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """price_snapshots 갭 감지 헬스체크.

    최근 7 평일 중 스냅샷이 없는 날짜를 반환한다.
    응답 예시:
    {
      "status": "ok" | "degraded",
      "checked_weekdays": 7,
      "missing_snapshots": ["2026-03-18"],
      "present_snapshots": ["2026-03-17", ...]
    }
    """
    today = date.today()
    weekdays = _last_n_weekdays(7, today)

    # 해당 날짜에 스냅샷이 존재하는지 확인 (ticker 무관, 최소 1건)
    result = await db.execute(
        select(PriceSnapshot.snapshot_date)
        .where(PriceSnapshot.snapshot_date.in_(weekdays))
        .group_by(PriceSnapshot.snapshot_date)
        .having(func.count() > 0)
    )
    present_dates = {row[0] for row in result.all()}

    missing: list[str] = []
    present: list[str] = []
    for d in sorted(weekdays):
        if d in present_dates:
            present.append(d.isoformat())
        else:
            missing.append(d.isoformat())

    status = "ok" if not missing else "degraded"
    return {
        "status": status,
        "checked_weekdays": len(weekdays),
        "missing_snapshots": missing,
        "present_snapshots": present,
    }


@router.get("/holdings-reconciliation")
async def holdings_reconciliation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """보유 수량 정합성 검사.

    각 보유 종목에 대해 거래 이력(BUY - SELL) 합산 수량과
    현재 holdings.quantity 간의 불일치를 감지한다.
    삭제된 거래(deleted_at IS NOT NULL)는 제외한다.

    응답 예시:
    {
      "status": "ok" | "degraded",
      "checked_holdings": 10,
      "mismatches": [
        {
          "portfolio_id": 1,
          "holding_id": 3,
          "ticker": "005930",
          "holdings_quantity": "10.000000",
          "transaction_net_quantity": "8.000000",
          "diff": "-2.000000"
        }
      ]
    }
    """
    # 현재 사용자의 포트폴리오 ID 목록
    portfolio_result = await db.execute(
        select(Portfolio.id).where(Portfolio.user_id == current_user.id)
    )
    portfolio_ids = [row[0] for row in portfolio_result.all()]

    if not portfolio_ids:
        return {"status": "ok", "checked_holdings": 0, "mismatches": []}

    # 보유 종목 조회
    holdings_result = await db.execute(
        select(Holding).where(Holding.portfolio_id.in_(portfolio_ids))
    )
    holdings = holdings_result.scalars().all()

    if not holdings:
        return {"status": "ok", "checked_holdings": 0, "mismatches": []}

    # 거래 이력 BUY/SELL 합산 — ticker + portfolio_id 기준
    txn_result = await db.execute(
        select(
            Transaction.portfolio_id,
            Transaction.ticker,
            func.sum(
                case(
                    (Transaction.type == "BUY", Transaction.quantity),
                    else_=-Transaction.quantity,
                )
            ).label("net_quantity"),
        )
        .where(
            Transaction.portfolio_id.in_(portfolio_ids),
            Transaction.deleted_at.is_(None),
        )
        .group_by(Transaction.portfolio_id, Transaction.ticker)
    )
    txn_net: dict[tuple[int, str], Decimal] = {
        (row.portfolio_id, row.ticker): row.net_quantity or Decimal("0")
        for row in txn_result.all()
    }

    mismatches = []
    for h in holdings:
        key = (h.portfolio_id, h.ticker)
        net_qty = txn_net.get(key, Decimal("0"))
        diff = net_qty - h.quantity
        if abs(diff) > Decimal("0.000001"):
            mismatches.append(
                {
                    "portfolio_id": h.portfolio_id,
                    "holding_id": h.id,
                    "ticker": h.ticker,
                    "holdings_quantity": str(h.quantity),
                    "transaction_net_quantity": str(net_qty),
                    "diff": str(diff),
                }
            )

    status = "ok" if not mismatches else "degraded"
    return {
        "status": status,
        "checked_holdings": len(holdings),
        "mismatches": mismatches,
    }


@router.get("/orphan-records")
async def orphan_records_check(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """고아 레코드(orphan records) 감지 헬스체크.

    현재 사용자의 보유 종목, 거래 내역, 동기화 로그 중
    존재하지 않는 portfolio_id를 참조하는 레코드 수를 반환한다.

    CASCADE DELETE가 올바르게 작동한다면 항상 0이어야 한다.
    비정상적인 데이터 마이그레이션이나 직접 INSERT 이후 감지용으로 사용한다.

    응답 예시:
    {
      "status": "ok" | "degraded",
      "orphan_holdings": 0,
      "orphan_transactions": 0,
      "orphan_sync_logs": 0
    }
    """
    # 현재 사용자의 유효한 포트폴리오 ID 목록
    portfolio_result = await db.execute(
        select(Portfolio.id).where(Portfolio.user_id == current_user.id)
    )
    valid_portfolio_ids = {row[0] for row in portfolio_result.all()}

    if not valid_portfolio_ids:
        return {
            "status": "ok",
            "orphan_holdings": 0,
            "orphan_transactions": 0,
            "orphan_sync_logs": 0,
        }

    # 고아 보유 종목: 사용자 소유이나 유효하지 않은 portfolio_id 참조
    orphan_holdings_result = await db.execute(
        select(func.count()).select_from(Holding).where(
            Holding.portfolio_id.notin_(valid_portfolio_ids),
        )
    )
    orphan_holdings = orphan_holdings_result.scalar() or 0

    # 고아 거래 내역
    orphan_txn_result = await db.execute(
        select(func.count()).select_from(Transaction).where(
            Transaction.portfolio_id.notin_(valid_portfolio_ids),
        )
    )
    orphan_transactions = orphan_txn_result.scalar() or 0

    # 고아 동기화 로그
    orphan_sync_result = await db.execute(
        select(func.count()).select_from(SyncLog).where(
            SyncLog.user_id == current_user.id,
            SyncLog.portfolio_id.notin_(valid_portfolio_ids),
        )
    )
    orphan_sync_logs = orphan_sync_result.scalar() or 0

    total_orphans = orphan_holdings + orphan_transactions + orphan_sync_logs
    status = "ok" if total_orphans == 0 else "degraded"

    return {
        "status": status,
        "orphan_holdings": orphan_holdings,
        "orphan_transactions": orphan_transactions,
        "orphan_sync_logs": orphan_sync_logs,
    }
