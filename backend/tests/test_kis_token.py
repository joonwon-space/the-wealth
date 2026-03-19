"""Unit tests for KIS token service TTL parsing and cache logic."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.unit
class TestIssueTokenTtlParsing:
    """Tests for TTL calculation from access_token_token_expired field."""

    @patch("app.services.kis_token.httpx.AsyncClient")
    async def test_ttl_parsed_from_expiry_string(self, mock_client_cls: MagicMock) -> None:
        """TTL is calculated correctly from access_token_token_expired."""
        from app.services.kis_token import _issue_token

        # Set expiry 12 hours from now
        future = datetime.now() + timedelta(hours=12)
        expires_str = future.strftime("%Y-%m-%d %H:%M:%S")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "access_token": "test_token_abc",
            "access_token_token_expired": expires_str,
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        token, ttl = await _issue_token("key", "secret")

        assert token == "test_token_abc"
        # 12 hours = 43200 seconds; allow ±60 seconds tolerance
        assert abs(ttl - 43200) < 60

    @patch("app.services.kis_token.httpx.AsyncClient")
    async def test_ttl_falls_back_to_default_on_missing_expiry(
        self, mock_client_cls: MagicMock
    ) -> None:
        """Falls back to _TOKEN_TTL_SECONDS when expiry field is missing."""
        from app.services.kis_token import _TOKEN_TTL_SECONDS, _issue_token

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"access_token": "test_token_abc"}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        token, ttl = await _issue_token("key", "secret")

        assert token == "test_token_abc"
        assert ttl == _TOKEN_TTL_SECONDS

    @patch("app.services.kis_token.httpx.AsyncClient")
    async def test_ttl_falls_back_on_invalid_expiry_format(
        self, mock_client_cls: MagicMock
    ) -> None:
        """Falls back to default TTL when expiry string cannot be parsed."""
        from app.services.kis_token import _TOKEN_TTL_SECONDS, _issue_token

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "access_token": "test_token_abc",
            "access_token_token_expired": "not-a-date",
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        token, ttl = await _issue_token("key", "secret")

        assert token == "test_token_abc"
        assert ttl == _TOKEN_TTL_SECONDS

    @patch("app.services.kis_token.httpx.AsyncClient")
    async def test_ttl_minimum_60_seconds(self, mock_client_cls: MagicMock) -> None:
        """TTL is at least 60 seconds even if expiry is already past."""
        from app.services.kis_token import _issue_token

        # Already-expired token
        past = datetime.now() - timedelta(hours=1)
        expires_str = past.strftime("%Y-%m-%d %H:%M:%S")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "access_token": "test_token_abc",
            "access_token_token_expired": expires_str,
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        token, ttl = await _issue_token("key", "secret")

        assert token == "test_token_abc"
        assert ttl >= 60


@pytest.mark.unit
class TestGetKisAccessToken:
    @patch("app.core.redis_cache.aioredis")
    async def test_returns_cached_token(self, mock_aioredis: MagicMock) -> None:
        """Returns token from Redis cache without calling KIS API."""
        from app.services.kis_token import get_kis_access_token

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="cached_token_xyz")
        mock_redis.__aenter__ = AsyncMock(return_value=mock_redis)
        mock_redis.__aexit__ = AsyncMock(return_value=False)
        mock_aioredis.from_url.return_value = mock_redis

        token = await get_kis_access_token("key", "secret")

        assert token == "cached_token_xyz"
        mock_redis.get.assert_called_once()

    @patch("app.services.kis_token._issue_token", new_callable=AsyncMock)
    @patch("app.core.redis_cache.aioredis")
    async def test_issues_new_token_on_cache_miss(
        self, mock_aioredis: MagicMock, mock_issue: AsyncMock
    ) -> None:
        """Issues new token and caches it when Redis has no entry."""
        from app.services.kis_token import get_kis_access_token

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        mock_redis.__aenter__ = AsyncMock(return_value=mock_redis)
        mock_redis.__aexit__ = AsyncMock(return_value=False)
        mock_aioredis.from_url.return_value = mock_redis

        mock_issue.return_value = ("fresh_token_abc", 86400)

        token = await get_kis_access_token("key", "secret")

        assert token == "fresh_token_abc"
        mock_issue.assert_awaited_once_with("key", "secret")
        mock_redis.setex.assert_called_once()
