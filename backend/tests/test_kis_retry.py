"""Unit tests for KIS HTTP retry wrapper (kis_retry.kis_request / kis_get).

Policy: when KIS returns HTTP 429, retry once after a short jitter.
Non-429 responses (including rt_cd != "0" inside a 200 body) pass through
unchanged — those are the caller's responsibility.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.kis_retry import kis_get, kis_request


class _FakeClient:
    """Minimal stand-in for httpx.AsyncClient — records each request and
    returns scripted responses in order."""

    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict]] = []

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:  # noqa: ANN003
        self.calls.append((method, url, kwargs))
        return self._responses.pop(0)


def _resp(status: int, body: bytes = b"") -> httpx.Response:
    return httpx.Response(status_code=status, content=body)


@pytest.mark.unit
class TestKisRetry:
    @pytest.mark.asyncio
    async def test_200_returns_immediately_without_retry(self) -> None:
        client = _FakeClient([_resp(200, b'{"ok":1}')])
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            resp = await kis_request(client, "GET", "https://x/y")
        assert resp.status_code == 200
        assert len(client.calls) == 1
        mock_sleep.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_429_retries_once_then_returns_success(self) -> None:
        client = _FakeClient([_resp(429), _resp(200, b"{}")])
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            resp = await kis_request(client, "GET", "https://x/y")
        assert resp.status_code == 200
        assert len(client.calls) == 2
        mock_sleep.assert_awaited_once()
        # Jitter must fall inside the documented window
        wait = mock_sleep.call_args.args[0]
        assert 0.05 <= wait <= 0.15

    @pytest.mark.asyncio
    async def test_429_persists_after_final_retry_returns_last_response(
        self,
    ) -> None:
        client = _FakeClient([_resp(429), _resp(429)])
        with patch("asyncio.sleep", new_callable=AsyncMock):
            resp = await kis_request(client, "GET", "https://x/y", max_retries=1)
        assert resp.status_code == 429
        assert len(client.calls) == 2  # original + 1 retry

    @pytest.mark.asyncio
    async def test_max_retries_zero_disables_retry(self) -> None:
        client = _FakeClient([_resp(429)])
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            resp = await kis_request(client, "GET", "https://x/y", max_retries=0)
        assert resp.status_code == 429
        assert len(client.calls) == 1
        mock_sleep.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_500_is_not_retried(self) -> None:
        """5xx is server error — caller decides; retry wrapper only targets 429."""
        client = _FakeClient([_resp(500)])
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            resp = await kis_request(client, "GET", "https://x/y")
        assert resp.status_code == 500
        assert len(client.calls) == 1
        mock_sleep.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_kis_get_forwards_args_to_request(self) -> None:
        client = _FakeClient([_resp(200, b"{}")])
        await kis_get(
            client,
            "https://x/y",
            headers={"tr_id": "ABC"},
            params={"a": "1"},
        )
        method, url, kwargs = client.calls[0]
        assert method == "GET"
        assert url == "https://x/y"
        assert kwargs["headers"] == {"tr_id": "ABC"}
        assert kwargs["params"] == {"a": "1"}
