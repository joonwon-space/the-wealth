"""미체결 주문에 의해 잘못 생성된 transaction을 soft delete하는 일회성 스크립트.

Phase 1 적용 전에 pending 주문이 즉시 transaction/holding을 생성했던 버그로 인해
실제로 체결되지 않은 주문의 transaction이 남아있을 수 있다.

이 스크립트는:
1. order_source="kis"인 transaction을 조회
2. 해당 order_no의 Order가 pending 또는 cancelled 상태인 경우 soft delete
3. --dry-run 모드로 먼저 확인 후 실행 가능

Usage:
    # Dry run (변경 없이 확인만)
    python scripts/fix_pending_transactions.py --dry-run

    # 실행
    python scripts/fix_pending_transactions.py
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, and_

from app.db.session import AsyncSessionLocal
from app.models.order import Order
from app.models.transaction import Transaction


async def fix_pending_transactions(dry_run: bool = True) -> None:
    """미체결 주문의 잘못된 transaction을 soft delete한다."""
    async with AsyncSessionLocal() as db:
        # order_source="kis"이고 아직 soft delete 안 된 transaction 조회
        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.order_source == "kis",
                    Transaction.order_no.isnot(None),
                    Transaction.deleted_at.is_(None),
                )
            )
        )
        kis_transactions = list(result.scalars().all())

        if not kis_transactions:
            print("KIS 주문 연관 transaction이 없습니다.")
            return

        print(f"KIS 주문 연관 transaction {len(kis_transactions)}건 발견")

        # 각 transaction의 order_no로 Order 상태 확인
        order_nos = {t.order_no for t in kis_transactions if t.order_no}
        order_result = await db.execute(
            select(Order).where(Order.order_no.in_(order_nos))
        )
        orders = {o.order_no: o for o in order_result.scalars().all()}

        to_delete = []
        for txn in kis_transactions:
            order = orders.get(txn.order_no)
            if order is None:
                # Order가 없는 경우 (삭제됨) — skip
                continue
            if order.status in ("pending", "cancelled", "failed"):
                to_delete.append((txn, order))

        if not to_delete:
            print("정리할 transaction이 없습니다. 모든 KIS transaction이 정상입니다.")
            return

        print(f"\n정리 대상: {len(to_delete)}건")
        print("-" * 80)
        for txn, order in to_delete:
            print(
                f"  Transaction #{txn.id}: "
                f"ticker={txn.ticker} type={txn.type} qty={txn.quantity} "
                f"order_no={txn.order_no} → Order status={order.status}"
            )

        if dry_run:
            print(f"\n[DRY RUN] {len(to_delete)}건이 soft delete 대상입니다.")
            print("실제 삭제하려면 --dry-run 없이 실행하세요.")
            return

        now = datetime.now(timezone.utc)
        for txn, _order in to_delete:
            txn.deleted_at = now

        await db.commit()
        print(f"\n{len(to_delete)}건 soft delete 완료.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="미체결 주문의 잘못된 transaction soft delete"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="변경 없이 대상만 확인",
    )
    args = parser.parse_args()
    asyncio.run(fix_pending_transactions(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
