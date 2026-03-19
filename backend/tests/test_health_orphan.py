"""고아 레코드(orphan records) 헬스체크 통합 테스트.

GET /health/orphan-records 엔드포인트를 통해
존재하지 않는 portfolio_id를 참조하는 레코드 감지 기능을 검증한다.
"""

import pytest
from httpx import AsyncClient


async def _register_and_get_token(
    client: AsyncClient, email: str = "orphan@example.com"
) -> str:
    """Helper: register user and return access token."""
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
class TestOrphanRecordsCheck:
    async def test_no_portfolios_returns_ok(self, client: AsyncClient) -> None:
        """포트폴리오가 없는 사용자는 orphan 없음."""
        token = await _register_and_get_token(client, "orphan_empty@example.com")
        resp = await client.get("/health/orphan-records", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["orphan_holdings"] == 0
        assert data["orphan_transactions"] == 0
        assert data["orphan_sync_logs"] == 0

    async def test_with_valid_portfolio_returns_ok(self, client: AsyncClient) -> None:
        """유효한 포트폴리오가 있을 때 고아 레코드 없음."""
        token = await _register_and_get_token(client, "orphan_valid@example.com")
        auth = _auth_headers(token)

        # 포트폴리오 생성
        port_resp = await client.post(
            "/portfolios",
            json={"name": "테스트 포트폴리오"},
            headers=auth,
        )
        assert port_resp.status_code == 201
        pid = port_resp.json()["id"]

        # 종목 추가
        holding_resp = await client.post(
            f"/portfolios/{pid}/holdings",
            json={
                "ticker": "005930",
                "name": "삼성전자",
                "quantity": "10",
                "avg_price": "70000",
            },
            headers=auth,
        )
        assert holding_resp.status_code == 201

        # 고아 레코드 없어야 함
        resp = await client.get("/health/orphan-records", headers=auth)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["orphan_holdings"] == 0
        assert data["orphan_transactions"] == 0

    async def test_requires_authentication(self, client: AsyncClient) -> None:
        """미인증 요청은 401/403 반환."""
        resp = await client.get("/health/orphan-records")
        assert resp.status_code in (401, 403)

    async def test_after_portfolio_delete_no_orphans(self, client: AsyncClient) -> None:
        """포트폴리오 삭제 후 CASCADE DELETE로 고아 없어야 함."""
        token = await _register_and_get_token(client, "orphan_cascade@example.com")
        auth = _auth_headers(token)

        # 포트폴리오 생성
        port_resp = await client.post(
            "/portfolios",
            json={"name": "삭제할 포트폴리오"},
            headers=auth,
        )
        pid = port_resp.json()["id"]

        # 종목 추가
        await client.post(
            f"/portfolios/{pid}/holdings",
            json={
                "ticker": "000660",
                "name": "SK하이닉스",
                "quantity": "5",
                "avg_price": "100000",
            },
            headers=auth,
        )

        # 포트폴리오 삭제
        del_resp = await client.delete(f"/portfolios/{pid}", headers=auth)
        assert del_resp.status_code == 204

        # CASCADE DELETE로 holdings도 삭제됨 — 고아 없어야 함
        resp = await client.get("/health/orphan-records", headers=auth)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["orphan_holdings"] == 0
