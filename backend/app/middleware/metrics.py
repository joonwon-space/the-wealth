"""API 응답시간 측정 미들웨어.

각 요청의 처리 시간을 계산하여:
- structlog 로그에 `process_time_ms` 필드로 기록한다.
- HTTP 응답 헤더 `X-Process-Time` (초 단위, 소수점 3자리)에 추가한다.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Measure API response time per request and expose via header + structlog."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)  # type: ignore[arg-type]
        elapsed_s = time.perf_counter() - start
        elapsed_ms = round(elapsed_s * 1000, 2)

        response.headers["X-Process-Time"] = f"{elapsed_s:.3f}"

        logger.info(
            "request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time_ms=elapsed_ms,
        )

        return response
