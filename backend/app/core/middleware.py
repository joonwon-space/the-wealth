"""HTTP security headers middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "X-XSS-Protection": "1; mode=block",
}

_HSTS_HEADER = "Strict-Transport-Security"
_HSTS_VALUE = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Append security-related HTTP response headers to every response."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        response: Response = await call_next(request)  # type: ignore[arg-type]
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if settings.ENVIRONMENT == "production":
            response.headers.setdefault(_HSTS_HEADER, _HSTS_VALUE)
        return response
