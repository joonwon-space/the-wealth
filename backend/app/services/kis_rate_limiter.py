"""KIS API 토큰 버킷 레이트 리미터 + 동시성 캡 (RL-001, RL-009).

두 계층의 보호 장치를 제공한다:

1. **토큰 버킷 (req/sec 제어)**
   - 초당 토큰 보충 속도(`KIS_RATE_LIMIT_PER_SEC`)와 버스트 한도(`KIS_RATE_LIMIT_BURST`).
   - 다수 코루틴이 동시에 대기할 때 staircase(계단식) 묶음 발사가 일어나지 않도록
     `_next_release` 시간 예약 방식으로 정렬한다 — N번째 대기자는 (N-burst)/rate
     초 뒤에 단독 발사된다.

2. **동시성 세마포어 (in-flight 연결 수 제어)**
   - `KIS_MAX_CONCURRENCY` 개의 HTTP 요청만 동시에 KIS 로 진행 가능.
   - HTTP 응답이 도착해 with 블록을 빠져나갈 때 슬롯이 반납된다.
   - KIS 가 connection-level 로 던지는 `ConnectTimeout` 패턴(429 가 아닌)을
     방어하기 위한 핵심 장치.

설정 (`app.core.config.Settings`):
  KIS_RATE_LIMIT_PER_SEC   초당 토큰 보충 속도 (기본 5.0)
  KIS_RATE_LIMIT_BURST     최대 버스트 크기 (기본 12)
  KIS_MAX_CONCURRENCY      동시 in-flight 요청 최대 (기본 6)
  KIS_MOCK_MODE            True 면 둘 다 비활성화 (로컬/테스트)

권장 사용법 — context manager (rate token + concurrency slot):

    from app.services.kis_rate_limiter import kis_call_slot

    async with kis_call_slot():
        resp = await client.get(...)   # HTTP 응답 도착 시점에 슬롯 반납

레거시 — `acquire()` 는 rate token 만 처리한다. 신규 코드는 가급적 `kis_call_slot`
을 사용하라.
"""

from __future__ import annotations

import asyncio
import threading
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Observability counters (RL-005)
# ---------------------------------------------------------------------------

_timeout_counter_lock = threading.Lock()
_timeout_counter: int = 0


def get_timeout_counter() -> int:
    """현재까지 누적된 acquire() 타임아웃 횟수 반환."""
    with _timeout_counter_lock:
        return _timeout_counter


def _increment_timeout_counter() -> None:
    global _timeout_counter
    with _timeout_counter_lock:
        _timeout_counter += 1


# ---------------------------------------------------------------------------
# Token bucket implementation
# ---------------------------------------------------------------------------

_P95_WARN_THRESHOLD_SEC: float = 0.5  # 대기 시간이 이 값 이상이면 P95 힌트 로그 발행


class KisRateLimiter:
    """비동기-안전 토큰 버킷 레이트 리미터.

    RL-009: `_next_release` 시간 예약을 통해 다수 대기자가 같은 wait 값을
    동시에 받아 한꺼번에 깨어나는 staircase 패턴을 제거한다.

    Args:
        rate:      초당 토큰 보충 속도 (tokens/second).
        burst:     최대 버스트 크기. 버킷이 꽉 찼을 때 보유할 수 있는 최대 토큰 수.
        mock_mode: True 이면 _consume() 이 항상 0 을 반환 (대기 없음).
    """

    def __init__(
        self,
        rate: float = settings.KIS_RATE_LIMIT_PER_SEC,
        burst: int = settings.KIS_RATE_LIMIT_BURST,
        mock_mode: bool = settings.KIS_MOCK_MODE,
    ) -> None:
        self._rate = rate
        self._burst = float(burst)
        self._mock_mode = mock_mode
        self._tokens: float = float(burst)
        now = time.monotonic()
        self._last_refill: float = now
        # 다음 토큰 발급 가능 시각. 대기자가 진입할 때마다 1/rate 만큼 미래로 밀려
        # 후속 대기자에게 더 긴 wait 를 주어 발사 시각을 분산시킨다.
        self._next_release: float = now
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Internal helpers (synchronous — called while holding the lock)
    # ------------------------------------------------------------------

    def _refill(self) -> None:
        """경과 시간만큼 토큰을 보충. 버스트 상한 초과 불가."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
        self._last_refill = now

    def _consume(self, n: int = 1) -> float:
        """n 개 토큰 소비를 시도한다.

        Returns:
            0.0  — 토큰을 즉시 획득함.
            >0.0 — 대기해야 하는 시간(초).
        """
        if self._mock_mode:
            return 0.0

        self._refill()

        # 버킷에 충분한 토큰이 있으면 즉시 발사.
        if self._tokens >= n:
            self._tokens -= n
            return 0.0

        # 부족분만큼 미래 시각을 예약. 다른 대기자도 같은 경로로 들어오면
        # _next_release 가 누적 전진하므로 wait 값이 자연스럽게 차등 부여된다.
        deficit = n - self._tokens
        self._tokens = 0.0
        now = time.monotonic()
        scheduled = max(self._next_release, now) + deficit / self._rate
        self._next_release = scheduled
        return scheduled - now

    def available_tokens(self) -> float:
        """현재 버킷의 사용 가능한 토큰 수 (근사값, 잠금 없음)."""
        self._refill()
        return self._tokens

    # ------------------------------------------------------------------
    # Async public API
    # ------------------------------------------------------------------

    async def acquire(self, n: int = 1, timeout: Optional[float] = None) -> None:
        """토큰 n 개를 비동기로 획득한다.

        Args:
            n:       획득할 토큰 수 (기본 1).
            timeout: 이 시간(초) 내에 토큰을 획득하지 못하면 asyncio.TimeoutError.

        Raises:
            asyncio.TimeoutError: timeout 초과 시.
        """
        async with self._lock:
            wait = self._consume(n)

        if wait <= 0.0:
            return

        if wait >= _P95_WARN_THRESHOLD_SEC:
            logger.warning(
                "[KisRateLimiter] P95 slow acquire: wait=%.3fs — "
                "consider raising KIS_RATE_LIMIT_BURST or KIS_RATE_LIMIT_PER_SEC",
                wait,
            )

        if timeout is not None and wait > timeout:
            _increment_timeout_counter()
            logger.warning(
                "[KisRateLimiter] acquire timeout: required_wait=%.3fs timeout=%.3fs "
                "(cumulative_timeouts=%d)",
                wait,
                timeout,
                get_timeout_counter(),
            )
            raise asyncio.TimeoutError(
                f"KIS rate limiter: required wait {wait:.3f}s exceeds timeout {timeout:.3f}s"
            )

        await asyncio.sleep(wait)


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_limiter = KisRateLimiter()

# /oauth2/tokenP has its own 1/s cap per KIS policy — must not share the
# general REST bucket, otherwise a token refresh burst would starve price
# lookups and vice-versa.
_token_limiter = KisRateLimiter(
    rate=settings.KIS_TOKEN_RATE_LIMIT_PER_SEC,
    burst=settings.KIS_TOKEN_RATE_LIMIT_BURST,
    mock_mode=settings.KIS_MOCK_MODE,
)

# Concurrency cap — independent of req/sec. Bounds the number of in-flight
# KIS HTTP requests so a fan-out batch (e.g. asyncio.gather over N holdings)
# cannot open N TCP connections simultaneously.
_concurrency_sem: asyncio.Semaphore = asyncio.Semaphore(settings.KIS_MAX_CONCURRENCY)


async def acquire(n: int = 1, timeout: Optional[float] = None) -> None:
    """모듈 수준 싱글톤 레이트 리미터에서 토큰을 획득한다 (rate-only).

    동시 in-flight 연결 수는 통제하지 않는다. 신규 코드는 `kis_call_slot()`
    context manager 를 사용하라.
    """
    await _limiter.acquire(n=n, timeout=timeout)


async def acquire_token_issuance(timeout: Optional[float] = None) -> None:
    """/oauth2/tokenP 1건/s 전용 리미터. kis_token._issue_token 에서만 호출."""
    await _token_limiter.acquire(n=1, timeout=timeout)


@asynccontextmanager
async def kis_call_slot(
    n: int = 1, timeout: Optional[float] = None
) -> AsyncIterator[None]:
    """동시성 슬롯 + 레이트 토큰을 함께 획득하는 context manager.

    슬롯은 with 블록을 빠져나갈 때(예외 포함) 자동 반납된다. 권장 패턴:

        async with kis_call_slot():
            resp = await client.get(...)

    레이트 리미터 토큰은 with 진입 시점에 소비되며, 슬롯은 HTTP 응답이 도착할
    때까지 유지된다. 이로써 KIS 와의 동시 connection 수가
    `KIS_MAX_CONCURRENCY` 이하로 유지된다.

    Mock mode 에서는 어느 쪽도 차단하지 않는다.
    """
    if settings.KIS_MOCK_MODE:
        yield
        return

    async with _concurrency_sem:
        await _limiter.acquire(n=n, timeout=timeout)
        yield
