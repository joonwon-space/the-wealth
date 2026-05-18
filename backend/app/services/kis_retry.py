"""KIS HTTP 요청 재시도 래퍼.

재시도 대상:
  1. HTTP 429 또는 200 + `rt_cd="EGW00201"` (레이트 거절 — 두 경로 모두)
  2. HTTP 5xx (500/502/503/504 — KIS 내부 분산 정책 거절). **GET 만** —
     POST/PUT/PATCH/DELETE 는 서버가 처리한 뒤 응답만 못 받은 케이스가
     있어 중복 실행 위험이 있다 (주문 placement/취소 등).
  3. ConnectError / TimeoutException (네트워크 계층)

백오프: exponential + jitter (AWS / Stripe 표준). attempt n 의 대기
시간은 [base_min*2^(n-1), base_max*2^(n-1)] 범위에서 균등 난수, 상한은
`_RETRY_CAP_MS`. Thundering-herd 방지 + KIS 가 일시 폭주를 흡수할
시간 확보.

KIS 정책 안내: "서버 내 분산 정책에 따라 일부 유량이 통과되지 않는 경우,
즉시 재호출" — 5xx 도 retry 가 권장된다. POST 가 retry 대상에서 제외된
이유는 idempotency 보장이 안 된 엔드포인트에서 동일 주문이 두 번
처리될 수 있기 때문 (주문 placement 는 `_ORDER_LOCK_PREFIX` Redis 락이
별도로 있지만, 그건 client 단의 중복 방지일 뿐 서버 처리 후 응답
유실 시점에는 작동하지 않는다).
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

# Exponential backoff jitter windows (base = attempt 1).
# attempt n  의 대기 시간 = randint(base_min * 2^(n-1), base_max * 2^(n-1)),
# 상한 _RETRY_CAP_MS.
_RETRY_BASE_MIN_MS = 50
_RETRY_BASE_MAX_MS = 200
_NETWORK_BASE_MIN_MS = 200
_NETWORK_BASE_MAX_MS = 500
_RETRY_CAP_MS = 3000


def _backoff_ms(attempt: int, base_min: int, base_max: int) -> int:
    """Exponential backoff with full jitter, capped at `_RETRY_CAP_MS`.

    attempt=1: base   |  attempt=2: 2x base  |  attempt=3: 4x base  | ...
    """
    factor = 2 ** (attempt - 1)
    lo = min(base_min * factor, _RETRY_CAP_MS)
    hi = min(base_max * factor, _RETRY_CAP_MS)
    if lo > hi:  # _RETRY_CAP_MS 에 둘 다 박혔을 때
        lo = hi
    return random.randint(lo, hi)


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


def _is_server_error(resp: httpx.Response) -> bool:
    """KIS 5xx — 즉시 재호출이 권장되는 일시 internal error."""
    return 500 <= resp.status_code < 600


async def kis_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """KIS HTTP 요청 — 429 / 5xx (GET) / 네트워크 에러를 exponential backoff
    로 최대 `max_retries`회 재시도한다.

    Args:
        client:       httpx AsyncClient.
        method:       "GET" | "POST" 등. 5xx retry 는 GET 만 — POST 류는
                      idempotency 가 없어 서버 처리 후 응답 유실 시 중복
                      실행 위험이 있다.
        url:          전체 URL.
        max_retries:  None 이면 settings.KIS_HTTP_MAX_RETRIES 사용.
        **kwargs:     client.request 에 그대로 전달.

    Returns:
        최종 응답. retry 한도 후에도 실패 상태가 지속되면 그 응답을 반환 —
        호출부에서 raise_for_status() 또는 rt_cd 검사로 실패 처리.
    """
    # Local import: avoid circular-import risk at module load time.
    from app.services.kis_rate_limiter import acquire as _reacquire_token

    retries = settings.KIS_HTTP_MAX_RETRIES if max_retries is None else max_retries
    network_retries = settings.KIS_HTTP_NETWORK_RETRY
    attempts = retries + 1
    method_upper = method.upper()
    can_retry_5xx = method_upper == "GET"

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
                wait_ms = _backoff_ms(
                    network_attempt, _NETWORK_BASE_MIN_MS, _NETWORK_BASE_MAX_MS
                )
                logger.warning(
                    "KIS %s %s network error (%s) — retry %d/%d after %dms",
                    method, url, exc, network_attempt, network_retries, wait_ms,
                )
                await asyncio.sleep(wait_ms / 1000.0)
                continue
            raise

        # 재시도 사유 판별
        retry_reason: str | None = None
        if _is_rate_limited(resp):
            retry_reason = "rate-limited"
        elif can_retry_5xx and _is_server_error(resp):
            retry_reason = "server-error"

        if retry_reason is None or attempt == attempts:
            return resp

        wait_ms = _backoff_ms(attempt, _RETRY_BASE_MIN_MS, _RETRY_BASE_MAX_MS)
        rt_cd = (
            resp.json().get("rt_cd")
            if resp.status_code == 200
            else None
        ) if retry_reason == "rate-limited" else None
        logger.warning(
            "KIS %s %s %s (status=%d rt_cd=%s) — retry %d/%d after %dms",
            method,
            url,
            retry_reason,
            resp.status_code,
            rt_cd,
            attempt,
            retries,
            wait_ms,
        )
        await asyncio.sleep(wait_ms / 1000.0)
        # 레이트 거절일 때만 토큰 재소비 — 5xx 는 KIS 측 internal error 라
        # 우리 rate-limit 위반과 무관하다.
        if retry_reason == "rate-limited":
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
