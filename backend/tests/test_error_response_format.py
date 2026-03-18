"""Tests for standardized error response format.

Verifies that all HTTP errors follow the envelope:
  {"error": {"code": "<CODE>", "message": "<detail>", "request_id": "<uuid>"}}

Also verifies that the X-Request-ID response header is set.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestErrorResponseFormat:
    async def test_404_not_found_uses_error_envelope(
        self, client: AsyncClient
    ) -> None:
        """Unknown route must return standardized error envelope with 404."""
        resp = await client.get("/nonexistent-endpoint-xyz")
        # FastAPI returns 404 for unknown routes
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        err = body["error"]
        assert "code" in err
        assert "message" in err
        assert "request_id" in err

    async def test_401_unauthorized_uses_error_envelope(
        self, client: AsyncClient
    ) -> None:
        """Accessing a protected endpoint without auth must use error envelope."""
        resp = await client.get("/portfolios")
        assert resp.status_code in (401, 403)
        body = resp.json()
        assert "error" in body
        err = body["error"]
        assert "code" in err
        assert "message" in err

    async def test_422_validation_error_uses_error_envelope(
        self, client: AsyncClient
    ) -> None:
        """Pydantic validation error must use error envelope."""
        resp = await client.post(
            "/auth/register",
            json={"email": "not-an-email", "password": "x"},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert "error" in body
        err = body["error"]
        assert "code" in err
        assert "message" in err

    async def test_400_duplicate_email_uses_error_envelope(
        self, client: AsyncClient
    ) -> None:
        """Application-level 400 error must use error envelope."""
        await client.post(
            "/auth/register",
            json={"email": "dupformat@test.com", "password": "Pass1234!"},
        )
        resp = await client.post(
            "/auth/register",
            json={"email": "dupformat@test.com", "password": "Pass1234!"},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert "error" in body
        err = body["error"]
        assert "code" in err
        assert "message" in err

    async def test_x_request_id_header_present(
        self, client: AsyncClient
    ) -> None:
        """Every response must include X-Request-ID header."""
        resp = await client.get("/health")
        assert "x-request-id" in resp.headers or "X-Request-ID" in resp.headers

    async def test_error_code_is_http_status_string(
        self, client: AsyncClient
    ) -> None:
        """error.code should be a non-empty string."""
        resp = await client.get("/portfolios")
        body = resp.json()
        err = body.get("error", {})
        assert isinstance(err.get("code"), str)
        assert len(err["code"]) > 0

    async def test_success_response_not_wrapped(
        self, client: AsyncClient
    ) -> None:
        """Success responses are NOT wrapped in error envelope."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert "error" not in body
        assert body.get("status") == "ok"
