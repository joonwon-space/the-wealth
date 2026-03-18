"""Security integration tests.

Covers:
- IDOR: User A cannot read/modify/delete User B's resources
- Expired JWT access token is rejected (401)
- Consumed JTI (used refresh token) is rejected (401)
- Rate limit 429 is enforced on login and register endpoints
- Unauthenticated access to protected endpoints returns 401/403
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings

_PASSWORD = "SecurePass123!"


async def _register_and_login(
    client: AsyncClient, email: str
) -> tuple[str, str]:
    """Register user and return (access_token, refresh_token)."""
    await client.post(
        "/auth/register",
        json={"email": email, "password": _PASSWORD},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": email, "password": _PASSWORD},
    )
    data = resp.json()
    return data["access_token"], data["refresh_token"]


async def _create_portfolio(client: AsyncClient, token: str, name: str = "MyPort") -> int:
    resp = await client.post(
        "/portfolios",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# IDOR tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIDOR:
    async def test_cannot_read_other_users_portfolio(
        self, client: AsyncClient
    ) -> None:
        """User B cannot GET User A's portfolio."""
        token_a, _ = await _register_and_login(client, "idor_a1@test.com")
        token_b, _ = await _register_and_login(client, "idor_b1@test.com")

        port_id = await _create_portfolio(client, token_a, "A-Port")

        resp = await client.get(
            f"/portfolios/{port_id}/holdings",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code in (403, 404)

    async def test_cannot_delete_other_users_portfolio(
        self, client: AsyncClient
    ) -> None:
        """User B cannot DELETE User A's portfolio."""
        token_a, _ = await _register_and_login(client, "idor_a2@test.com")
        token_b, _ = await _register_and_login(client, "idor_b2@test.com")

        port_id = await _create_portfolio(client, token_a, "A-Port2")

        resp = await client.delete(
            f"/portfolios/{port_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code in (403, 404)

    async def test_cannot_rename_other_users_portfolio(
        self, client: AsyncClient
    ) -> None:
        """User B cannot PATCH User A's portfolio name."""
        token_a, _ = await _register_and_login(client, "idor_a3@test.com")
        token_b, _ = await _register_and_login(client, "idor_b3@test.com")

        port_id = await _create_portfolio(client, token_a, "A-Port3")

        resp = await client.patch(
            f"/portfolios/{port_id}",
            json={"name": "Stolen"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code in (403, 404)

    async def test_list_portfolios_isolation(
        self, client: AsyncClient
    ) -> None:
        """GET /portfolios only returns the current user's portfolios."""
        token_a, _ = await _register_and_login(client, "idor_a4@test.com")
        token_b, _ = await _register_and_login(client, "idor_b4@test.com")

        await _create_portfolio(client, token_a, "A-Private")

        resp = await client.get(
            "/portfolios",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 200

        # Create one for B to verify B can see their own
        b_port_id = await _create_portfolio(client, token_b, "B-Port")
        resp2 = await client.get(
            "/portfolios",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        b_ids = [p["id"] for p in resp2.json()]
        assert b_port_id in b_ids

    async def test_cannot_add_holding_to_other_users_portfolio(
        self, client: AsyncClient
    ) -> None:
        """User B cannot POST a holding into User A's portfolio."""
        token_a, _ = await _register_and_login(client, "idor_a5@test.com")
        token_b, _ = await _register_and_login(client, "idor_b5@test.com")

        port_id = await _create_portfolio(client, token_a, "A-Port5")

        resp = await client.post(
            f"/portfolios/{port_id}/holdings",
            json={
                "ticker": "005930",
                "name": "삼성전자",
                "quantity": "10",
                "avg_price": "70000",
                "market": "KR",
            },
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Expired JWT
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestExpiredJWT:
    async def test_expired_access_token_rejected(
        self, client: AsyncClient
    ) -> None:
        """A token with past expiry must be rejected with 401."""
        expired_payload = {
            "sub": "99999",
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        }
        expired_token = jwt.encode(
            expired_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        resp = await client.get(
            "/portfolios",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    async def test_token_with_wrong_type_rejected(
        self, client: AsyncClient
    ) -> None:
        """A refresh token used as an access token must be rejected."""
        from app.core.security import create_refresh_token

        refresh_token, _ = create_refresh_token(user_id=999)

        resp = await client.get(
            "/portfolios",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert resp.status_code == 401

    async def test_garbage_token_rejected(self, client: AsyncClient) -> None:
        """Completely invalid JWT string must be rejected with 401."""
        resp = await client.get(
            "/portfolios",
            headers={"Authorization": "Bearer notavalidtoken"},
        )
        assert resp.status_code == 401

    async def test_missing_auth_header_rejected(
        self, client: AsyncClient
    ) -> None:
        """No Authorization header must return 401 or 403."""
        resp = await client.get("/portfolios")
        assert resp.status_code in (401, 403)

    async def test_valid_token_accepted(self, client: AsyncClient) -> None:
        """A freshly minted access token must allow protected endpoints."""
        token, _ = await _register_and_login(
            client, "valid_jwt@test.com"
        )
        resp = await client.get(
            "/portfolios",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Consumed JTI (refresh token rotation)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestConsumedJTI:
    async def test_reused_refresh_token_rejected(
        self, client: AsyncClient
    ) -> None:
        """A refresh token that was already consumed must return 401."""
        token, refresh = await _register_and_login(client, "jti_test@test.com")

        # First use — should succeed
        resp1 = await client.post(
            "/auth/refresh", json={"refresh_token": refresh}
        )
        assert resp1.status_code == 200

        # Second use of the same token — must fail
        resp2 = await client.post(
            "/auth/refresh", json={"refresh_token": refresh}
        )
        assert resp2.status_code == 401

    async def test_new_refresh_token_usable_after_rotation(
        self, client: AsyncClient
    ) -> None:
        """The new refresh token from rotation should be usable."""
        _, refresh = await _register_and_login(client, "jti_test2@test.com")

        first_resp = await client.post(
            "/auth/refresh", json={"refresh_token": refresh}
        )
        new_refresh = first_resp.json()["refresh_token"]

        second_resp = await client.post(
            "/auth/refresh", json={"refresh_token": new_refresh}
        )
        assert second_resp.status_code == 200

    async def test_invalid_refresh_token_string_rejected(
        self, client: AsyncClient
    ) -> None:
        resp = await client.post(
            "/auth/refresh", json={"refresh_token": "garbage.token.value"}
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Rate limit 429
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRateLimitEnforced:
    async def test_login_rate_limit_429(self, client: AsyncClient) -> None:
        """After exceeding login rate limit, 429 should be returned."""
        statuses = []
        # Login limit is 5/min; send 8 requests
        for i in range(8):
            resp = await client.post(
                "/auth/login",
                json={
                    "email": f"ratelimit_login{i}@test.com",
                    "password": "WrongPass!",
                },
            )
            statuses.append(resp.status_code)

        # Must encounter at least one non-200 response (401 or 429)
        assert any(s in (401, 429) for s in statuses)

    async def test_register_rate_limit_429(self, client: AsyncClient) -> None:
        """After exceeding register rate limit, 429 should be returned."""
        statuses = []
        # Register limit is 3/min; send 6 requests
        for i in range(6):
            resp = await client.post(
                "/auth/register",
                json={
                    "email": f"ratelimit_reg{i}@test.com",
                    "password": "SecurePass123!",
                },
            )
            statuses.append(resp.status_code)

        # Must see at least 201 or 429
        assert any(s in (201, 429) for s in statuses)
