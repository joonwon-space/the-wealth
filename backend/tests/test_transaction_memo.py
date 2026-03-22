"""Transaction memo 기능 테스트 (단위 + 통합)."""

import pytest
from httpx import AsyncClient


@pytest.mark.unit
class TestTransactionMemoSchema:
    """TransactionMemoUpdate 스키마 단위 테스트."""

    def test_memo_none_by_default(self) -> None:
        """memo 필드는 기본값이 None."""
        from app.schemas.portfolio import TransactionMemoUpdate
        obj = TransactionMemoUpdate()
        assert obj.memo is None

    def test_memo_string_value(self) -> None:
        """memo에 문자열 저장."""
        from app.schemas.portfolio import TransactionMemoUpdate
        obj = TransactionMemoUpdate(memo="삼성전자 분할매수")
        assert obj.memo == "삼성전자 분할매수"

    def test_memo_max_length_500(self) -> None:
        """memo는 최대 500자."""
        from app.schemas.portfolio import TransactionMemoUpdate
        # Exactly 500 chars should be fine
        obj = TransactionMemoUpdate(memo="a" * 500)
        assert len(obj.memo) == 500  # type: ignore[arg-type]

    def test_memo_over_max_length_rejected(self) -> None:
        """501자 이상 memo는 거부된다."""
        from pydantic import ValidationError
        from app.schemas.portfolio import TransactionMemoUpdate
        with pytest.raises(ValidationError):
            TransactionMemoUpdate(memo="a" * 501)

    def test_memo_explicit_none(self) -> None:
        """memo를 명시적으로 None으로 지울 수 있다."""
        from app.schemas.portfolio import TransactionMemoUpdate
        obj = TransactionMemoUpdate(memo=None)
        assert obj.memo is None

    def test_transaction_response_includes_memo(self) -> None:
        """TransactionResponse에 memo 필드가 포함된다."""
        from app.schemas.portfolio import TransactionResponse
        fields = TransactionResponse.model_fields
        assert "memo" in fields

    def test_transaction_model_has_memo_column(self) -> None:
        """Transaction SQLAlchemy 모델에 memo 컬럼이 있다."""
        from app.models.transaction import Transaction
        assert hasattr(Transaction, "memo")


@pytest.mark.integration
class TestTransactionMemoAPI:
    """거래 메모 PATCH API 통합 테스트."""

    async def _setup(self, client: AsyncClient, email: str) -> tuple[str, int, int]:
        """Register, login, create portfolio and transaction. Return (token, pid, txn_id)."""
        await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
        resp = await client.post(
            "/auth/login", json={"email": email, "password": "Test1234!"}
        )
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        port = await client.post(
            "/portfolios", json={"name": "memo test"}, headers=headers
        )
        pid = port.json()["id"]
        txn = await client.post(
            f"/portfolios/{pid}/transactions",
            json={"ticker": "005930", "type": "BUY", "quantity": 10, "price": 70000},
            headers=headers,
        )
        txn_id = txn.json()["id"]
        return token, pid, txn_id

    async def test_patch_memo_set_value(self, client: AsyncClient) -> None:
        """거래에 메모를 저장할 수 있다."""
        token, pid, txn_id = await self._setup(client, "memo_set@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.patch(
            f"/portfolios/{pid}/transactions/{txn_id}",
            json={"memo": "분할 매수 1차"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["memo"] == "분할 매수 1차"

    async def test_patch_memo_clear_value(self, client: AsyncClient) -> None:
        """메모를 None으로 지울 수 있다."""
        token, pid, txn_id = await self._setup(client, "memo_clear@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        # First set memo
        await client.patch(
            f"/portfolios/{pid}/transactions/{txn_id}",
            json={"memo": "임시 메모"},
            headers=headers,
        )
        # Then clear it
        resp = await client.patch(
            f"/portfolios/{pid}/transactions/{txn_id}",
            json={"memo": None},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["memo"] is None

    async def test_patch_memo_default_null_in_response(
        self, client: AsyncClient
    ) -> None:
        """새 거래의 memo는 기본값 null이다."""
        token, pid, txn_id = await self._setup(client, "memo_default@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        # List transactions and verify memo is null
        resp = await client.get(f"/portfolios/{pid}/transactions", headers=headers)
        assert resp.status_code == 200
        txns = resp.json()
        assert len(txns) >= 1
        target = next((t for t in txns if t["id"] == txn_id), None)
        assert target is not None
        assert target["memo"] is None

    async def test_patch_memo_nonexistent_transaction(
        self, client: AsyncClient
    ) -> None:
        """존재하지 않는 거래에 메모 PATCH 시 404."""
        token, pid, _ = await self._setup(client, "memo_404@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.patch(
            f"/portfolios/{pid}/transactions/99999",
            json={"memo": "not found"},
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_patch_memo_idor_protection(self, client: AsyncClient) -> None:
        """다른 유저의 거래 메모를 수정할 수 없다 (IDOR 방지)."""
        token_a, pid_a, txn_id_a = await self._setup(client, "memo_idor_a@test.com")
        token_b, pid_b, _ = await self._setup(client, "memo_idor_b@test.com")
        headers_b = {"Authorization": f"Bearer {token_b}"}
        # User B tries to patch User A's transaction via User A's portfolio
        resp = await client.patch(
            f"/portfolios/{pid_a}/transactions/{txn_id_a}",
            json={"memo": "hacked"},
            headers=headers_b,
        )
        assert resp.status_code in (403, 404)

    async def test_patch_memo_over_500_chars_rejected(
        self, client: AsyncClient
    ) -> None:
        """501자 이상의 메모는 422로 거부된다."""
        token, pid, txn_id = await self._setup(client, "memo_toolong@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.patch(
            f"/portfolios/{pid}/transactions/{txn_id}",
            json={"memo": "a" * 501},
            headers=headers,
        )
        assert resp.status_code == 422
