"""Unit tests for app/core/security.py — targeting 90%+ coverage.

Tests cover:
- hash_password / verify_password
- create_access_token / create_refresh_token / decode_access_token / decode_refresh_token
- store_refresh_jti / verify_and_consume_refresh_jti
- revoke_all_refresh_tokens_for_user
- Edge cases: expired tokens, wrong type, missing sub/jti
"""

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    revoke_all_refresh_tokens_for_user,
    store_refresh_jti,
    verify_and_consume_refresh_jti,
    verify_password,
)


@pytest.mark.unit
class TestHashVerifyPassword:
    def test_hash_returns_string(self) -> None:
        hashed = hash_password("mypassword")
        assert isinstance(hashed, str)
        assert hashed != "mypassword"

    def test_verify_correct_password(self) -> None:
        hashed = hash_password("correct")
        assert verify_password("correct", hashed) is True

    def test_verify_wrong_password(self) -> None:
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_different_hashes_for_same_password(self) -> None:
        h1 = hash_password("same")
        h2 = hash_password("same")
        # bcrypt uses random salt — two hashes must differ
        assert h1 != h2


@pytest.mark.unit
class TestCreateDecodeAccessToken:
    def test_create_access_token_returns_string(self) -> None:
        token = create_access_token(user_id=1)
        assert isinstance(token, str)

    def test_decode_access_token_returns_user_id(self) -> None:
        token = create_access_token(user_id=42)
        result = decode_access_token(token)
        assert result == 42

    def test_decode_access_token_invalid_string(self) -> None:
        result = decode_access_token("not.a.token")
        assert result is None

    def test_decode_access_token_wrong_type_returns_none(self) -> None:
        """Token with type='refresh' must be rejected by decode_access_token."""
        payload = {
            "sub": "5",
            "type": "refresh",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        result = decode_access_token(token)
        assert result is None

    def test_decode_access_token_expired_returns_none(self) -> None:
        """Expired access token must return None."""
        payload = {
            "sub": "7",
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        result = decode_access_token(token)
        assert result is None

    def test_decode_access_token_missing_sub_returns_none(self) -> None:
        """Token without sub field must return None."""
        payload = {
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        result = decode_access_token(token)
        assert result is None

    def test_decode_access_token_wrong_secret_returns_none(self) -> None:
        payload = {
            "sub": "1",
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        }
        token = jwt.encode(payload, "wrong-secret", algorithm=settings.JWT_ALGORITHM)
        result = decode_access_token(token)
        assert result is None


@pytest.mark.unit
class TestCreateDecodeRefreshToken:
    def test_create_refresh_token_returns_tuple(self) -> None:
        token, jti = create_refresh_token(user_id=1)
        assert isinstance(token, str)
        assert isinstance(jti, str)
        assert len(jti) > 0

    def test_decode_refresh_token_valid(self) -> None:
        token, jti = create_refresh_token(user_id=99)
        result = decode_refresh_token(token)
        assert result is not None
        assert result["user_id"] == 99
        assert result["jti"] == jti

    def test_decode_refresh_token_invalid_string(self) -> None:
        result = decode_refresh_token("bad.token.here")
        assert result is None

    def test_decode_refresh_token_wrong_type_returns_none(self) -> None:
        """Token with type='access' must be rejected by decode_refresh_token."""
        payload = {
            "sub": "3",
            "type": "access",
            "jti": "some-jti",
            "exp": datetime.now(UTC) + timedelta(days=7),
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        result = decode_refresh_token(token)
        assert result is None

    def test_decode_refresh_token_expired_returns_none(self) -> None:
        payload = {
            "sub": "8",
            "type": "refresh",
            "jti": "some-jti",
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        result = decode_refresh_token(token)
        assert result is None

    def test_decode_refresh_token_missing_sub_returns_none(self) -> None:
        payload = {
            "type": "refresh",
            "jti": "some-jti",
            "exp": datetime.now(UTC) + timedelta(days=7),
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        result = decode_refresh_token(token)
        assert result is None

    def test_decode_refresh_token_missing_jti_returns_none(self) -> None:
        payload = {
            "sub": "10",
            "type": "refresh",
            "exp": datetime.now(UTC) + timedelta(days=7),
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        result = decode_refresh_token(token)
        assert result is None

    def test_decode_refresh_token_wrong_secret_returns_none(self) -> None:
        payload = {
            "sub": "1",
            "type": "refresh",
            "jti": "jti-value",
            "exp": datetime.now(UTC) + timedelta(days=7),
        }
        token = jwt.encode(payload, "wrong-secret", algorithm=settings.JWT_ALGORITHM)
        result = decode_refresh_token(token)
        assert result is None

    def test_unique_jti_per_token(self) -> None:
        _, jti1 = create_refresh_token(user_id=1)
        _, jti2 = create_refresh_token(user_id=1)
        assert jti1 != jti2


@pytest.mark.unit
class TestRedisJtiOperations:
    """Test Redis-backed JTI store/verify/revoke functions with mocked Redis."""

    @pytest.fixture
    def mock_redis(self) -> MagicMock:
        redis_mock = AsyncMock()
        redis_mock.__aenter__ = AsyncMock(return_value=redis_mock)
        redis_mock.__aexit__ = AsyncMock(return_value=None)
        return redis_mock

    async def test_store_refresh_jti_calls_setex(self, mock_redis: MagicMock) -> None:
        with patch("app.core.security.aioredis.from_url", return_value=mock_redis):
            await store_refresh_jti("test-jti", user_id=5)
        mock_redis.setex.assert_awaited_once()
        call_args = mock_redis.setex.await_args
        key = call_args[0][0]
        assert "test-jti" in key

    async def test_verify_and_consume_found(self, mock_redis: MagicMock) -> None:
        mock_redis.get = AsyncMock(return_value="42")
        mock_redis.delete = AsyncMock()
        with patch("app.core.security.aioredis.from_url", return_value=mock_redis):
            user_id = await verify_and_consume_refresh_jti("valid-jti")
        assert user_id == 42
        mock_redis.delete.assert_awaited_once()

    async def test_verify_and_consume_not_found(self, mock_redis: MagicMock) -> None:
        mock_redis.get = AsyncMock(return_value=None)
        with patch("app.core.security.aioredis.from_url", return_value=mock_redis):
            user_id = await verify_and_consume_refresh_jti("missing-jti")
        assert user_id is None

    async def test_revoke_all_scans_and_deletes_matching(
        self, mock_redis: MagicMock
    ) -> None:
        # First scan returns cursor=0 and matching keys
        mock_redis.scan = AsyncMock(
            return_value=(0, ["refresh_jti:jti-1", "refresh_jti:jti-2"])
        )
        mock_redis.get = AsyncMock(side_effect=["7", "99"])
        mock_redis.delete = AsyncMock()

        with patch("app.core.security.aioredis.from_url", return_value=mock_redis):
            await revoke_all_refresh_tokens_for_user(user_id=7)

        # Only the key whose value is "7" should be deleted
        mock_redis.delete.assert_awaited_once_with("refresh_jti:jti-1")

    async def test_revoke_all_multiple_scan_pages(
        self, mock_redis: MagicMock
    ) -> None:
        """When scan returns non-zero cursor first, loop continues."""
        # Page 1: cursor=5, one key belonging to user 3
        # Page 2: cursor=0, one key belonging to someone else
        mock_redis.scan = AsyncMock(
            side_effect=[
                (5, ["refresh_jti:jti-a"]),
                (0, ["refresh_jti:jti-b"]),
            ]
        )
        mock_redis.get = AsyncMock(side_effect=["3", "999"])
        mock_redis.delete = AsyncMock()

        with patch("app.core.security.aioredis.from_url", return_value=mock_redis):
            await revoke_all_refresh_tokens_for_user(user_id=3)

        assert mock_redis.scan.await_count == 2
        mock_redis.delete.assert_awaited_once_with("refresh_jti:jti-a")

    async def test_revoke_all_no_matching_keys(self, mock_redis: MagicMock) -> None:
        """If no keys match user_id, nothing is deleted."""
        mock_redis.scan = AsyncMock(return_value=(0, ["refresh_jti:jti-x"]))
        mock_redis.get = AsyncMock(return_value="999")
        mock_redis.delete = AsyncMock()

        with patch("app.core.security.aioredis.from_url", return_value=mock_redis):
            await revoke_all_refresh_tokens_for_user(user_id=1)

        mock_redis.delete.assert_not_awaited()
