"""인증 API 단위 테스트 (register, login, refresh)."""

import pytest
from httpx import AsyncClient

TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "SecurePass123!"


@pytest.mark.integration
class TestRegister:
    async def test_register_success(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/auth/register",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == TEST_EMAIL
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient) -> None:
        # First registration
        await client.post(
            "/auth/register",
            json={
                "email": "dup@example.com",
                "password": TEST_PASSWORD,
            },
        )
        # Duplicate
        resp = await client.post(
            "/auth/register",
            json={
                "email": "dup@example.com",
                "password": TEST_PASSWORD,
            },
        )
        assert resp.status_code == 400

    async def test_register_invalid_email(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": TEST_PASSWORD,
            },
        )
        assert resp.status_code == 422


@pytest.mark.integration
class TestLogin:
    async def test_login_success(self, client: AsyncClient) -> None:
        # Register first
        await client.post(
            "/auth/register",
            json={
                "email": "login@example.com",
                "password": TEST_PASSWORD,
            },
        )
        resp = await client.post(
            "/auth/login",
            json={
                "email": "login@example.com",
                "password": TEST_PASSWORD,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client: AsyncClient) -> None:
        await client.post(
            "/auth/register",
            json={
                "email": "wrong@example.com",
                "password": TEST_PASSWORD,
            },
        )
        resp = await client.post(
            "/auth/login",
            json={
                "email": "wrong@example.com",
                "password": "WrongPass999!",
            },
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/auth/login",
            json={
                "email": "nobody@example.com",
                "password": TEST_PASSWORD,
            },
        )
        assert resp.status_code == 401


@pytest.mark.integration
class TestRefresh:
    async def test_refresh_success(self, client: AsyncClient) -> None:
        await client.post(
            "/auth/register",
            json={
                "email": "refresh@example.com",
                "password": TEST_PASSWORD,
            },
        )
        login_resp = await client.post(
            "/auth/login",
            json={
                "email": "refresh@example.com",
                "password": TEST_PASSWORD,
            },
        )
        refresh_token = login_resp.json()["refresh_token"]

        resp = await client.post(
            "/auth/refresh",
            json={
                "refresh_token": refresh_token,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_invalid_token(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/auth/refresh",
            json={
                "refresh_token": "invalid.token.here",
            },
        )
        assert resp.status_code == 401

    async def test_refresh_token_rotation(self, client: AsyncClient) -> None:
        """After refresh, the old refresh token must be rejected (one-time use)."""
        await client.post(
            "/auth/register",
            json={"email": "rotation@example.com", "password": TEST_PASSWORD},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": "rotation@example.com", "password": TEST_PASSWORD},
        )
        original_refresh_token = login_resp.json()["refresh_token"]

        # First use — should succeed and return new tokens
        first_resp = await client.post(
            "/auth/refresh", json={"refresh_token": original_refresh_token}
        )
        assert first_resp.status_code == 200
        new_tokens = first_resp.json()
        assert new_tokens["refresh_token"] != original_refresh_token

        # Second use of the original token — must be rejected
        reuse_resp = await client.post(
            "/auth/refresh", json={"refresh_token": original_refresh_token}
        )
        assert reuse_resp.status_code == 401

    async def test_rotated_token_is_usable(self, client: AsyncClient) -> None:
        """The new refresh token obtained from rotation can itself be used once."""
        await client.post(
            "/auth/register",
            json={"email": "rotate2@example.com", "password": TEST_PASSWORD},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": "rotate2@example.com", "password": TEST_PASSWORD},
        )
        first_token = login_resp.json()["refresh_token"]

        second_resp = await client.post(
            "/auth/refresh", json={"refresh_token": first_token}
        )
        second_token = second_resp.json()["refresh_token"]

        third_resp = await client.post(
            "/auth/refresh", json={"refresh_token": second_token}
        )
        assert third_resp.status_code == 200
        assert "access_token" in third_resp.json()

    async def test_refresh_missing_token_returns_401(self, client: AsyncClient) -> None:
        """Refresh with empty/missing token returns 401."""
        resp = await client.post("/auth/refresh", json={"refresh_token": ""})
        assert resp.status_code == 401

    async def test_refresh_sets_cookies(self, client: AsyncClient) -> None:
        """Successful refresh should set HttpOnly auth cookies."""
        await client.post(
            "/auth/register",
            json={"email": "cookie@example.com", "password": TEST_PASSWORD},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": "cookie@example.com", "password": TEST_PASSWORD},
        )
        refresh_token = login_resp.json()["refresh_token"]
        refresh_resp = await client.post(
            "/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert refresh_resp.status_code == 200
        # Cookie headers should include set-cookie
        assert "set-cookie" in refresh_resp.headers


@pytest.mark.integration
class TestChangePassword:
    async def test_change_password_success(self, client: AsyncClient) -> None:
        await client.post(
            "/auth/register",
            json={"email": "changepw@example.com", "password": TEST_PASSWORD},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": "changepw@example.com", "password": TEST_PASSWORD},
        )
        token = login_resp.json()["access_token"]

        resp = await client.post(
            "/auth/change-password",
            json={"current_password": TEST_PASSWORD, "new_password": "NewPass9999!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

    async def test_change_password_wrong_current(self, client: AsyncClient) -> None:
        await client.post(
            "/auth/register",
            json={"email": "changepw2@example.com", "password": TEST_PASSWORD},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": "changepw2@example.com", "password": TEST_PASSWORD},
        )
        token = login_resp.json()["access_token"]

        resp = await client.post(
            "/auth/change-password",
            json={"current_password": "WrongCurrent!", "new_password": "NewPass9999!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    async def test_change_password_too_short(self, client: AsyncClient) -> None:
        await client.post(
            "/auth/register",
            json={"email": "changepw3@example.com", "password": TEST_PASSWORD},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": "changepw3@example.com", "password": TEST_PASSWORD},
        )
        token = login_resp.json()["access_token"]

        resp = await client.post(
            "/auth/change-password",
            json={"current_password": TEST_PASSWORD, "new_password": "short"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    async def test_change_password_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/auth/change-password",
            json={"current_password": TEST_PASSWORD, "new_password": "NewPass9999!"},
        )
        assert resp.status_code in (401, 403)

    async def test_new_password_works_after_change(self, client: AsyncClient) -> None:
        """After changing password, old password is rejected and new one works."""
        await client.post(
            "/auth/register",
            json={"email": "changepw4@example.com", "password": TEST_PASSWORD},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": "changepw4@example.com", "password": TEST_PASSWORD},
        )
        token = login_resp.json()["access_token"]
        new_pass = "NewPass9999!"

        await client.post(
            "/auth/change-password",
            json={"current_password": TEST_PASSWORD, "new_password": new_pass},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Old password should fail
        old_resp = await client.post(
            "/auth/login",
            json={"email": "changepw4@example.com", "password": TEST_PASSWORD},
        )
        assert old_resp.status_code == 401

        # New password should work
        new_resp = await client.post(
            "/auth/login",
            json={"email": "changepw4@example.com", "password": new_pass},
        )
        assert new_resp.status_code == 200


@pytest.mark.integration
class TestLogout:
    async def test_logout_success(self, client: AsyncClient) -> None:
        await client.post(
            "/auth/register",
            json={"email": "logout@example.com", "password": TEST_PASSWORD},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": "logout@example.com", "password": TEST_PASSWORD},
        )
        token = login_resp.json()["access_token"]

        resp = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

    async def test_logout_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.post("/auth/logout")
        assert resp.status_code in (401, 403)

    async def test_logout_clears_cookies(self, client: AsyncClient) -> None:
        """Logout response should clear auth cookies."""
        await client.post(
            "/auth/register",
            json={"email": "logout2@example.com", "password": TEST_PASSWORD},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": "logout2@example.com", "password": TEST_PASSWORD},
        )
        token = login_resp.json()["access_token"]

        resp = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204
        # Cookies should be deleted (set with empty value or max-age=0)
        cookie_headers = resp.headers.get_list("set-cookie")
        assert len(cookie_headers) > 0  # At least one cookie is being cleared
