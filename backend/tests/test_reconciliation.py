"""Reconciliation 서비스 단위 테스트."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.user import User
from app.core.security import hash_password
from app.services.kis_account import KisHolding
from app.services.reconciliation import reconcile_holdings


@pytest.mark.unit
class TestReconciliation:
    async def test_insert_new_holdings(self, db: AsyncSession) -> None:
        """KIS에 있지만 DB에 없는 종목은 INSERT."""
        user = User(email="recon1@test.com", hashed_password=hash_password("test"))
        db.add(user)
        await db.commit()
        await db.refresh(user)

        portfolio = Portfolio(user_id=user.id, name="test")
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)

        kis_holdings = [
            KisHolding(
                ticker="005930",
                name="삼성전자",
                quantity=Decimal("10"),
                avg_price=Decimal("70000"),
            ),
        ]
        counts = await reconcile_holdings(db, portfolio.id, kis_holdings)
        assert counts["inserted"] == 1
        assert counts["updated"] == 0
        assert counts["deleted"] == 0

    async def test_update_changed_holdings(self, db: AsyncSession) -> None:
        """수량/단가가 다르면 UPDATE."""
        user = User(email="recon2@test.com", hashed_password=hash_password("test"))
        db.add(user)
        await db.commit()
        await db.refresh(user)

        portfolio = Portfolio(user_id=user.id, name="test")
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)

        holding = Holding(
            portfolio_id=portfolio.id,
            ticker="005930",
            name="삼성전자",
            quantity=Decimal("10"),
            avg_price=Decimal("70000"),
        )
        db.add(holding)
        await db.commit()

        kis_holdings = [
            KisHolding(
                ticker="005930",
                name="삼성전자",
                quantity=Decimal("20"),
                avg_price=Decimal("72000"),
            ),
        ]
        counts = await reconcile_holdings(db, portfolio.id, kis_holdings)
        assert counts["updated"] == 1
        assert counts["inserted"] == 0
        assert counts["deleted"] == 0

    async def test_delete_missing_holdings(self, db: AsyncSession) -> None:
        """DB에 있지만 KIS에 없는 종목은 DELETE."""
        user = User(email="recon3@test.com", hashed_password=hash_password("test"))
        db.add(user)
        await db.commit()
        await db.refresh(user)

        portfolio = Portfolio(user_id=user.id, name="test")
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)

        holding = Holding(
            portfolio_id=portfolio.id,
            ticker="005930",
            name="삼성전자",
            quantity=Decimal("10"),
            avg_price=Decimal("70000"),
        )
        db.add(holding)
        await db.commit()

        counts = await reconcile_holdings(db, portfolio.id, [])
        assert counts["deleted"] == 1
        assert counts["inserted"] == 0
        assert counts["updated"] == 0

    async def test_mixed_operations(self, db: AsyncSession) -> None:
        """INSERT + UPDATE + DELETE 동시 발생."""
        user = User(email="recon4@test.com", hashed_password=hash_password("test"))
        db.add(user)
        await db.commit()
        await db.refresh(user)

        portfolio = Portfolio(user_id=user.id, name="test")
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)

        # DB에 삼성전자, SK하이닉스 보유
        db.add(
            Holding(
                portfolio_id=portfolio.id,
                ticker="005930",
                name="삼성전자",
                quantity=Decimal("10"),
                avg_price=Decimal("70000"),
            )
        )
        db.add(
            Holding(
                portfolio_id=portfolio.id,
                ticker="000660",
                name="SK하이닉스",
                quantity=Decimal("5"),
                avg_price=Decimal("120000"),
            )
        )
        await db.commit()

        # KIS: 삼성전자(수량 변경) + 카카오(신규) — SK하이닉스 없음(청산)
        kis_holdings = [
            KisHolding(
                ticker="005930",
                name="삼성전자",
                quantity=Decimal("20"),
                avg_price=Decimal("72000"),
            ),
            KisHolding(
                ticker="035720",
                name="카카오",
                quantity=Decimal("30"),
                avg_price=Decimal("50000"),
            ),
        ]
        counts = await reconcile_holdings(db, portfolio.id, kis_holdings)
        assert counts["inserted"] == 1  # 카카오
        assert counts["updated"] == 1  # 삼성전자
        assert counts["deleted"] == 1  # SK하이닉스
