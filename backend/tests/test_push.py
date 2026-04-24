"""Web Push subscription API tests."""

import pytest
from httpx import AsyncClient


async def _register_and_get_token(
    client: AsyncClient, email: str = "push@example.com"
) -> str:
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


SAMPLE_ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc123"
SAMPLE_KEYS = {
    "p256dh": "BHdkXZq2-0" * 5 + "abcdefghij1234567890",
    "auth": "deadbeefcafebabe1234",
}


@pytest.mark.integration
class TestPushPublicKey:
    async def test_public_key_endpoint_returns_shape(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get("/push/public-key")
        assert resp.status_code == 200
        body = resp.json()
        assert "public_key" in body
        assert "enabled" in body
        # In test env the VAPID keys are empty ⇒ enabled is False.
        assert body["enabled"] is False


@pytest.mark.integration
class TestPushSubscribe:
    async def test_subscribe_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/push/subscribe",
            json={
                "endpoint": SAMPLE_ENDPOINT + "-noauth",
                "keys": SAMPLE_KEYS,
            },
        )
        assert resp.status_code in (401, 403)

    async def test_subscribe_creates_record(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "push_create@example.com")
        resp = await client.post(
            "/push/subscribe",
            headers=_auth_headers(token),
            json={
                "endpoint": SAMPLE_ENDPOINT + "-create",
                "keys": SAMPLE_KEYS,
                "user_agent": "pytest/test",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["endpoint"] == SAMPLE_ENDPOINT + "-create"
        assert body["user_agent"] == "pytest/test"
        assert isinstance(body["id"], int)

    async def test_subscribe_upserts_by_endpoint(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "push_upsert@example.com")
        endpoint = SAMPLE_ENDPOINT + "-upsert"
        first = await client.post(
            "/push/subscribe",
            headers=_auth_headers(token),
            json={"endpoint": endpoint, "keys": SAMPLE_KEYS},
        )
        assert first.status_code == 201
        first_id = first.json()["id"]

        # Re-post with a new UA — same endpoint → same row, refreshed.
        second = await client.post(
            "/push/subscribe",
            headers=_auth_headers(token),
            json={
                "endpoint": endpoint,
                "keys": SAMPLE_KEYS,
                "user_agent": "updated-ua",
            },
        )
        assert second.status_code == 201
        assert second.json()["id"] == first_id
        assert second.json()["user_agent"] == "updated-ua"


@pytest.mark.integration
class TestPushUnsubscribe:
    async def test_unsubscribe_removes_record(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "push_unsub@example.com")
        endpoint = SAMPLE_ENDPOINT + "-unsub"
        await client.post(
            "/push/subscribe",
            headers=_auth_headers(token),
            json={"endpoint": endpoint, "keys": SAMPLE_KEYS},
        )
        resp = await client.delete(
            f"/push/subscribe?endpoint={endpoint}",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 204

    async def test_unsubscribe_unknown_returns_404(
        self, client: AsyncClient
    ) -> None:
        token = await _register_and_get_token(client, "push_unsub_404@example.com")
        resp = await client.delete(
            "/push/subscribe?endpoint=https://nowhere.invalid/sub",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404

    async def test_cannot_unsubscribe_other_users_endpoint(
        self, client: AsyncClient
    ) -> None:
        """IDOR check: user A can't delete user B's subscription."""
        token_a = await _register_and_get_token(client, "push_owner@example.com")
        token_b = await _register_and_get_token(client, "push_thief@example.com")
        endpoint = SAMPLE_ENDPOINT + "-idor"
        await client.post(
            "/push/subscribe",
            headers=_auth_headers(token_a),
            json={"endpoint": endpoint, "keys": SAMPLE_KEYS},
        )
        resp = await client.delete(
            f"/push/subscribe?endpoint={endpoint}",
            headers=_auth_headers(token_b),
        )
        assert resp.status_code == 404
