"""KIS HTTP 요청 재시도 래퍼.

KIS 정책: "서버 내 분산 정책에 따라 일부 유량이 통과되지 않는 경우, 즉시 재호출"
→ 레이트 거절(HTTP 429 또는 200+rt_cd=EGW00201) 수신 시 짧은 지터 후 1회 재시도.

KIS는 레이트 초과를 두 경로로 알린다:
  1. HTTP 429 (네트워크 계층)
  2. HTTP 200 + body `rt_cd="EGW00201"` (애플리케이션 계층 — "초당 거래건수 초과")

주의: 본 래퍼는 **읽기 전용/멱등 요청에만** 사용한다. 주문 생성/취소는 중복
실행 위험이 있으므로 재시도 대상이 아니다 (각 콜사이트에서 직접 사용 금지).
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_KIS_RATELIMIT_RT_CD = "EGW00201"
_JITTER_MIN_MS = 50
_JITTER_MAX_MS = 150
_NETWORK_JITTER_MIN_MS = 200
_NETWORK_JITTER_MAX_MS = 500


def _is_rate_limited(resp: httpx.Response) -> bool:
    """429 OR 200+rt_cd=EGW00201 — KIS 레이트 거절의 두 경로 모두 감지.

    Tolerant of mock Response objects in tests: any exception raised while
    inspecting the body is treated as "not rate-limited" so a bogus/partial
    mock response cannot accidentally trigger a retry.
    """
    if resp.status_code == 429:
        return True
    if resp.status_code != 200:
        return False
    try:
        body = resp.json()
    except Exception:
        return False
    return isinstance(body, dict) and body.get("rt_cd") == _KIS_RATELIMIT_RT_CD


async def kis_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """KIS HTTP 요청. 429 수신 시 지터 후 최대 `max_retries`회 재시도.

    Args:
        client:       httpx AsyncClient.
        method:       "GET" | "POST" (읽기/멱등만 허용; 주문 엔드포인트는 사용 금지).
        url:          전체 URL.
        max_retries:  None이면 settings.KIS_HTTP_MAX_RETRIES 사용 (기본 1).
        **kwargs:     client.request에 그대로 전달 (headers, params, json, etc.).

    Returns:
        최종 응답. 재시도 후에도 429면 그 응답을 반환 — 호출부에서
        raise_for_status() 또는 rt_cd 검사로 실패 처리.
    """
    # Local import: avoid circular-import risk at module load time.
    from app.services.kis_rate_limiter import acquire as _reacquire_token

    retries = settings.KIS_HTTP_MAX_RETRIES if max_retries is None else max_retries
    network_retries = settings.KIS_HTTP_NETWORK_RETRY
    attempts = retries + 1
    method_upper = method.upper()

    # Dispatch via the convenience methods on httpx.AsyncClient so tests that
    # mock `client.get` / `client.post` directly continue to work.
    async def _do_request() -> httpx.Response:
        if method_upper == "GET":
            return await client.get(url, **kwargs)
        if method_upper == "POST":
            return await client.post(url, **kwargs)
        return await client.request(method_upper, url, **kwargs)

    network_attempt = 0
    for attempt in range(1, attempts + 1):
        try:
            resp = await _do_request()
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            if network_attempt < network_retries:
                network_attempt += 1
                wait_ms = random.randint(_NETWORK_JITTER_MIN_MS, _NETWORK_JITTER_MAX_MS)
                logger.warning(
                    "KIS %s %s network error (%s) — retry %d/%d after %dms",
                    method, url, exc, network_attempt, network_retries, wait_ms,
                )
                await asyncio.sleep(wait_ms / 1000.0)
                continue
            raise

        if not _is_rate_limited(resp) or attempt == attempts:
            return resp

        wait_ms = random.randint(_JITTER_MIN_MS, _JITTER_MAX_MS)
        logger.warning(
            "KIS %s %s rate-limited (status=%d rt_cd=%s) — retry %d/%d after %dms",
            method,
            url,
            resp.status_code,
            resp.json().get("rt_cd") if resp.status_code == 200 else None,
            attempt,
            retries,
            wait_ms,
        )
        await asyncio.sleep(wait_ms / 1000.0)
        # Re-consume a rate-limiter token so the retry respects the 18/s budget.
        # Without this, N concurrent 429s would spike past the per-second cap.
        await _reacquire_token()

    # Unreachable: the loop either returns on success/final attempt or continues.
    raise RuntimeError("kis_retry: unreachable")


async def kis_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_retries: int | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """client.get() 대체 — 429 재시도 포함. 읽기 전용."""
    return await kis_request(client, "GET", url, max_retries=max_retries, **kwargs)
