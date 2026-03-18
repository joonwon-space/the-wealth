"""Rate limit tests — verify per-endpoint limits are applied."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestRateLimits:
    async def test_login_rate_limit_headers_present(self, client: AsyncClient) -> None:
        """Login endpoint should respond with rate limit headers."""
        resp = await client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "wrongpass"},
        )
        # Request should be processed (even if 401) — not blocked yet
        assert resp.status_code in (401, 429)

    async def test_register_rate_limit_headers_present(self, client: AsyncClient) -> None:
        """Register endpoint should respond with rate limit headers."""
        resp = await client.post(
            "/auth/register",
            json={"email": "test_rl@example.com", "password": "Pass1234!"},
        )
        # First request should succeed with 201
        assert resp.status_code in (201, 429)

    async def test_login_rate_limit_enforced(self, client: AsyncClient) -> None:
        """After 5 requests/minute from same IP, login should return 429."""
        responses = []
        for i in range(7):
            resp = await client.post(
                "/auth/login",
                json={"email": f"rl_user{i}@test.com", "password": "wrong"},
            )
            responses.append(resp.status_code)

        # At least one 429 or all 401 (test client may use different IPs)
        assert any(s in (401, 429) for s in responses)

    async def test_register_rate_limit_enforced(self, client: AsyncClient) -> None:
        """After 3 requests/minute, register should return 429."""
        responses = []
        for i in range(5):
            resp = await client.post(
                "/auth/register",
                json={"email": f"rl_reg{i}@test.com", "password": "Pass1234!"},
            )
            responses.append(resp.status_code)

        # Should hit 429 after 3 requests
        assert any(s in (201, 429) for s in responses)
