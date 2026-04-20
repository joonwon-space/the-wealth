"""KIS HTTP 요청 재시도 래퍼.

KIS 정책: "서버 내 분산 정책에 따라 일부 유량이 통과되지 않는 경우, 즉시 재호출"
→ HTTP 429 수신 시 짧은 지터 후 1회 재시도.

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

_RETRY_STATUS_CODES: frozenset[int] = frozenset({429})
_JITTER_MIN_MS = 50
_JITTER_MAX_MS = 150


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
    retries = settings.KIS_HTTP_MAX_RETRIES if max_retries is None else max_retries
    attempts = retries + 1

    last_resp: httpx.Response | None = None
    for attempt in range(1, attempts + 1):
        resp = await client.request(method, url, **kwargs)
        last_resp = resp
        if resp.status_code not in _RETRY_STATUS_CODES or attempt == attempts:
            return resp

        wait_ms = random.randint(_JITTER_MIN_MS, _JITTER_MAX_MS)
        logger.warning(
            "KIS %s %s returned %d — retry %d/%d after %dms",
            method,
            url,
            resp.status_code,
            attempt,
            retries,
            wait_ms,
        )
        await asyncio.sleep(wait_ms / 1000.0)

    assert last_resp is not None  # loop guarantees assignment
    return last_resp


async def kis_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_retries: int | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """client.get() 대체 — 429 재시도 포함. 읽기 전용."""
    return await kis_request(client, "GET", url, max_retries=max_retries, **kwargs)
