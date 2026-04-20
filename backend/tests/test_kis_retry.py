"""Unit tests for KIS HTTP retry wrapper (kis_retry.kis_request / kis_get).

Policy: when KIS reports rate-limit rejection — either HTTP 429 or HTTP 200
with `rt_cd="EGW00201"` — retry once after a short jitter. Other non-200
statuses (5xx) and application errors with different `rt_cd` pass through
unchanged.
"""

import json
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

    async def get(self, url: str, **kwargs) -> httpx.Response:  # noqa: ANN003
        self.calls.append(("GET", url, kwargs))
        return self._responses.pop(0)

    async def post(self, url: str, **kwargs) -> httpx.Response:  # noqa: ANN003
        self.calls.append(("POST", url, kwargs))
        return self._responses.pop(0)

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:  # noqa: ANN003
        self.calls.append((method.upper(), url, kwargs))
        return self._responses.pop(0)


def _resp(status: int, body: bytes = b"") -> httpx.Response:
    return httpx.Response(status_code=status, content=body)


def _kis_json(rt_cd: str, **extra: object) -> httpx.Response:
    """Mimic a KIS 200 JSON envelope with the given rt_cd."""
    payload = {"rt_cd": rt_cd, "msg1": "mock", **extra}
    return httpx.Response(
        status_code=200,
        content=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
    )


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
    async def test_200_with_egw00201_triggers_retry(self) -> None:
        """KIS reports rate-limit rejection as 200 + rt_cd=EGW00201 — must retry."""
        client = _FakeClient([_kis_json("EGW00201"), _kis_json("0", output={"ok": 1})])
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
             patch(
                "app.services.kis_rate_limiter.acquire",
                new_callable=AsyncMock,
             ) as mock_acquire:
            resp = await kis_request(client, "GET", "https://x/y")
        assert resp.status_code == 200
        assert resp.json()["rt_cd"] == "0"
        assert len(client.calls) == 2
        mock_sleep.assert_awaited_once()
        mock_acquire.assert_awaited_once()  # re-acquire on retry (PERF-001)

    @pytest.mark.asyncio
    async def test_200_with_other_rt_cd_is_not_retried(self) -> None:
        """Application errors with a non-rate-limit rt_cd must NOT retry — caller handles."""
        client = _FakeClient([_kis_json("EGW00999", msg1="invalid input")])
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            resp = await kis_request(client, "GET", "https://x/y")
        assert resp.status_code == 200
        assert resp.json()["rt_cd"] == "EGW00999"
        assert len(client.calls) == 1
        mock_sleep.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_429_retry_reacquires_rate_limit_token(self) -> None:
        """Retry after 429 must consume a new rate-limiter token (PERF-001)."""
        client = _FakeClient([_resp(429), _resp(200, b"{}")])
        with patch("asyncio.sleep", new_callable=AsyncMock), \
             patch(
                "app.services.kis_rate_limiter.acquire",
                new_callable=AsyncMock,
             ) as mock_acquire:
            await kis_request(client, "GET", "https://x/y")
        mock_acquire.assert_awaited_once()

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
