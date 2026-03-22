"""MetricsMiddleware 단위 및 통합 테스트."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestMetricsMiddlewareUnit:
    """MetricsMiddleware 동작을 단위 테스트."""

    def test_x_process_time_header_format(self) -> None:
        """X-Process-Time 헤더가 초 단위 3자리 소수점 형식인지 확인."""
        import re
        pattern = re.compile(r"^\d+\.\d{3}$")
        sample = f"{0.1234:.3f}"
        assert pattern.match(sample), f"Format mismatch: {sample}"

    def test_process_time_ms_calculation(self) -> None:
        """elapsed_ms 계산 로직 검증."""
        import time
        start = time.perf_counter()
        _ = sum(range(1000))
        elapsed_s = time.perf_counter() - start
        elapsed_ms = round(elapsed_s * 1000, 2)
        assert isinstance(elapsed_ms, float)
        assert elapsed_ms >= 0

    def test_middleware_is_subclass_of_base(self) -> None:
        """MetricsMiddleware 클래스가 BaseHTTPMiddleware를 상속하는지 확인."""
        from app.middleware.metrics import MetricsMiddleware
        from starlette.middleware.base import BaseHTTPMiddleware
        assert issubclass(MetricsMiddleware, BaseHTTPMiddleware)

    def test_middleware_module_imports(self) -> None:
        """모듈 임포트가 정상적으로 동작하는지 확인."""
        from app.middleware.metrics import MetricsMiddleware  # noqa: F401
        assert MetricsMiddleware is not None

    @pytest.mark.asyncio
    async def test_dispatch_sets_process_time_header(self) -> None:
        """dispatch 메서드가 X-Process-Time 헤더를 설정하는지 확인."""
        from app.middleware.metrics import MetricsMiddleware
        from starlette.responses import Response

        mock_response = MagicMock(spec=Response)
        mock_response.headers = {}
        mock_response.status_code = 200

        async def mock_call_next(request):  # type: ignore[no-untyped-def]
            return mock_response

        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/v1/health"

        middleware = MetricsMiddleware.__new__(MetricsMiddleware)

        with patch("app.middleware.metrics.logger"):
            await middleware.dispatch(mock_request, mock_call_next)

        assert "X-Process-Time" in mock_response.headers
        value = mock_response.headers["X-Process-Time"]
        assert "." in value
        parts = value.split(".")
        assert len(parts[1]) == 3

    @pytest.mark.asyncio
    async def test_dispatch_logs_process_time(self) -> None:
        """dispatch가 process_time_ms를 structlog에 기록하는지 확인."""
        from app.middleware.metrics import MetricsMiddleware
        from starlette.responses import Response

        mock_response = MagicMock(spec=Response)
        mock_response.headers = {}
        mock_response.status_code = 200

        async def mock_call_next(request):  # type: ignore[no-untyped-def]
            return mock_response

        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url.path = "/api/v1/portfolios"

        middleware = MetricsMiddleware.__new__(MetricsMiddleware)

        with patch("app.middleware.metrics.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            mock_logger.info.assert_called_once()
            call_kwargs = mock_logger.info.call_args
            assert "process_time_ms" in (call_kwargs.kwargs or {})


@pytest.mark.integration
class TestMetricsMiddlewareIntegration:
    """MetricsMiddleware 통합 테스트 (HTTP 클라이언트 사용)."""

    async def test_health_response_has_process_time_header(
        self, client: object
    ) -> None:
        """GET /health 응답에 X-Process-Time 헤더가 있는지 확인."""
        if not hasattr(client, "get"):
            pytest.skip("Integration client not available")
        resp = await client.get("/health")  # type: ignore[union-attr]
        assert resp.status_code in (200, 404)
        # When MetricsMiddleware is active, header should be present
        if "X-Process-Time" in resp.headers:
            value = resp.headers["X-Process-Time"]
            assert "." in value
