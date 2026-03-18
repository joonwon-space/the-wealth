"""SecurityHeadersMiddleware 테스트 (모든 응답에 보안 헤더 포함 확인)."""

import pytest
from httpx import AsyncClient

EXPECTED_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "X-XSS-Protection": "1; mode=block",
}


@pytest.mark.integration
class TestSecurityHeadersOnPublicEndpoints:
    async def test_health_check_has_security_headers(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        for header, value in EXPECTED_HEADERS.items():
            assert resp.headers.get(header) == value, (
                f"Missing or wrong value for header '{header}': "
                f"expected '{value}', got '{resp.headers.get(header)}'"
            )

    async def test_x_content_type_options_on_health(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    async def test_x_frame_options_on_health(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    async def test_referrer_policy_on_health(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    async def test_permissions_policy_on_health(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.headers.get("Permissions-Policy") == "camera=(), microphone=(), geolocation=()"

    async def test_x_xss_protection_on_health(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"


@pytest.mark.integration
class TestSecurityHeadersOnAuthEndpoints:
    async def test_register_response_has_security_headers(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/auth/register",
            json={"email": "sec_reg@example.com", "password": "Test1234!"},
        )
        assert resp.status_code == 201
        for header, value in EXPECTED_HEADERS.items():
            assert resp.headers.get(header) == value, (
                f"Missing or wrong value for header '{header}'"
            )

    async def test_login_response_has_security_headers(self, client: AsyncClient) -> None:
        await client.post(
            "/auth/register",
            json={"email": "sec_login@example.com", "password": "Test1234!"},
        )
        resp = await client.post(
            "/auth/login",
            json={"email": "sec_login@example.com", "password": "Test1234!"},
        )
        assert resp.status_code == 200
        for header, value in EXPECTED_HEADERS.items():
            assert resp.headers.get(header) == value, (
                f"Missing or wrong value for header '{header}'"
            )

    async def test_failed_login_response_has_security_headers(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "WrongPass123!"},
        )
        assert resp.status_code == 401
        for header, value in EXPECTED_HEADERS.items():
            assert resp.headers.get(header) == value, (
                f"Missing or wrong value for header '{header}'"
            )


@pytest.mark.integration
class TestSecurityHeadersOnProtectedEndpoints:
    async def test_unauthenticated_portfolios_has_security_headers(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get("/portfolios")
        assert resp.status_code in (401, 403)
        for header, value in EXPECTED_HEADERS.items():
            assert resp.headers.get(header) == value, (
                f"Missing or wrong value for header '{header}'"
            )

    async def test_authenticated_portfolios_has_security_headers(
        self, client: AsyncClient
    ) -> None:
        await client.post(
            "/auth/register",
            json={"email": "sec_port@example.com", "password": "Test1234!"},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": "sec_port@example.com", "password": "Test1234!"},
        )
        token = login_resp.json()["access_token"]

        resp = await client.get(
            "/portfolios", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        for header, value in EXPECTED_HEADERS.items():
            assert resp.headers.get(header) == value, (
                f"Missing or wrong value for header '{header}'"
            )

    async def test_not_found_response_has_security_headers(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get("/nonexistent-endpoint-xyz")
        for header, value in EXPECTED_HEADERS.items():
            assert resp.headers.get(header) == value, (
                f"Missing or wrong value for header '{header}' on 404 response"
            )
