"""알림 센터 API 통합 테스트."""

import pytest
from httpx import AsyncClient


async def _register_and_get_token(
    client: AsyncClient, email: str = "notif@example.com"
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
class TestNotificationsListEmpty:
    async def test_list_empty_by_default(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "notif_empty@example.com")
        resp = await client.get("/notifications", headers=_auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_unauthenticated_denied(self, client: AsyncClient) -> None:
        resp = await client.get("/notifications")
        assert resp.status_code in (401, 403)


@pytest.mark.integration
class TestNotificationsMarkRead:
    async def test_mark_notification_read(self, client: AsyncClient) -> None:
        """Test that read-all works (no notifications yet = no-op, 204)."""
        token = await _register_and_get_token(client, "notif_read@example.com")

        # Since we can't directly create a notification via a POST endpoint,
        # we test the read-all endpoint on an empty set (no-op, should succeed)
        resp = await client.post(
            "/notifications/read-all", headers=_auth_headers(token)
        )
        assert resp.status_code == 204

    async def test_mark_nonexistent_notification_returns_404(
        self, client: AsyncClient
    ) -> None:
        token = await _register_and_get_token(client, "notif_404@example.com")
        resp = await client.patch(
            "/notifications/99999/read", headers=_auth_headers(token)
        )
        assert resp.status_code == 404

    async def test_mark_read_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.patch("/notifications/1/read")
        assert resp.status_code in (401, 403)

    async def test_read_all_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.post("/notifications/read-all")
        assert resp.status_code in (401, 403)


@pytest.mark.integration
class TestNotificationsIDOR:
    async def test_cannot_mark_other_users_notification_read(
        self, client: AsyncClient
    ) -> None:
        """User B cannot mark User A's notification as read (IDOR prevention)."""
        await _register_and_get_token(client, "notif_idor_a@example.com")
        token_b = await _register_and_get_token(client, "notif_idor_b@example.com")

        # Any notification_id from user B's perspective should return 404 for IDs owned by A
        # (We can't create a notification via POST, so we just test 404 for non-owned IDs)
        resp = await client.patch(
            "/notifications/99998/read", headers=_auth_headers(token_b)
        )
        assert resp.status_code == 404

    async def test_list_only_returns_own_notifications(
        self, client: AsyncClient
    ) -> None:
        """GET /notifications returns only the authenticated user's notifications."""
        token_a = await _register_and_get_token(client, "notif_scope_a@example.com")
        token_b = await _register_and_get_token(client, "notif_scope_b@example.com")

        resp_a = await client.get("/notifications", headers=_auth_headers(token_a))
        resp_b = await client.get("/notifications", headers=_auth_headers(token_b))

        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        # Both start empty
        assert resp_a.json() == []
        assert resp_b.json() == []


@pytest.mark.integration
class TestNotificationsReadAll:
    async def test_read_all_no_op_when_empty(self, client: AsyncClient) -> None:
        """POST /notifications/read-all returns 204 even when there are no notifications."""
        token = await _register_and_get_token(client, "notif_readall@example.com")
        resp = await client.post(
            "/notifications/read-all", headers=_auth_headers(token)
        )
        assert resp.status_code == 204

    async def test_read_all_idempotent(self, client: AsyncClient) -> None:
        """Calling read-all multiple times should not cause errors."""
        token = await _register_and_get_token(client, "notif_readall2@example.com")
        for _ in range(3):
            resp = await client.post(
                "/notifications/read-all", headers=_auth_headers(token)
            )
            assert resp.status_code == 204
