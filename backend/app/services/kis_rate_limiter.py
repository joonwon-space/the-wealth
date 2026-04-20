"""KIS API 토큰 버킷 레이트 리미터 (RL-001).

asyncio-safe token bucket: 초당 최대 요청 수와 버스트 허용량을 제어한다.

설정은 Settings에서 읽음:
  KIS_RATE_LIMIT_PER_SEC  — 초당 토큰 보충 속도 (기본 5.0)
  KIS_RATE_LIMIT_BURST    — 최대 버스트 크기 (기본 20)
  KIS_MOCK_MODE           — True이면 레이트 리밋 비활성화 (로컬 개발/테스트용)

사용법:
    from app.services.kis_rate_limiter import acquire

    async def call_kis_api(...):
        await acquire()          # 토큰 확보 후 KIS API 호출
        resp = await client.get(...)
"""

import asyncio
import threading
import time
from typing import Optional

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

    Args:
        rate:      초당 토큰 보충 속도 (tokens/second).
        burst:     최대 버스트 크기. 버킷이 꽉 찼을 때 보유할 수 있는 최대 토큰 수.
        mock_mode: True이면 _consume()이 항상 0을 반환 (대기 없음).
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
        self._tokens: float = float(burst)  # 시작 시 버스트 전체 보유
        self._last_refill: float = time.monotonic()
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
        """n개 토큰 소비를 시도한다.

        Returns:
            0.0  — 토큰을 즉시 획득함.
            >0.0 — 대기해야 하는 시간(초).
        """
        if self._mock_mode:
            return 0.0

        self._refill()
        if self._tokens >= n:
            self._tokens -= n
            return 0.0
        # 부족분 = n - available
        deficit = n - self._tokens
        self._tokens = 0.0
        return deficit / self._rate

    def available_tokens(self) -> float:
        """현재 버킷의 사용 가능한 토큰 수 (근사값, 잠금 없음)."""
        self._refill()
        return self._tokens

    # ------------------------------------------------------------------
    # Async public API
    # ------------------------------------------------------------------

    async def acquire(self, n: int = 1, timeout: Optional[float] = None) -> None:
        """토큰 n개를 비동기로 획득한다.

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

        # RL-005: 느린 대기 시 P95 힌트 로그
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


async def acquire(n: int = 1, timeout: Optional[float] = None) -> None:
    """모듈 수준 싱글톤 레이트 리미터에서 토큰을 획득한다.

    호출 예시:
        from app.services.kis_rate_limiter import acquire
        await acquire()
    """
    await _limiter.acquire(n=n, timeout=timeout)


async def acquire_token_issuance(timeout: Optional[float] = None) -> None:
    """/oauth2/tokenP 1건/s 전용 리미터. kis_token._issue_token에서만 호출."""
    await _token_limiter.acquire(n=1, timeout=timeout)
