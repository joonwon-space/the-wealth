from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import APIRouter, Depends, FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import alerts, analytics, auth, chart, dashboard, health, internal, notifications, portfolio_export, portfolios, prices, stocks, sync, users, watchlist
from app.api.prices import signal_sse_shutdown
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import configure_logging, generate_request_id, get_logger, get_request_id, set_request_id
from app.core.middleware import SecurityHeadersMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.db.session import get_db
from app.services.backup_health import get_last_backup_info
from app.services.kis_health import check_kis_api_health
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.stock_search import _load_stock_list

configure_logging()
logger = get_logger(__name__)

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.2,
        profiles_sample_rate=0.1,
        environment="production",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    start_scheduler()
    # Check KIS API connectivity at startup; sets KIS_AVAILABLE flag
    await check_kis_api_health()
    # Preload KRX + ETF stock list into Redis cache at startup
    try:
        stocks_list = await _load_stock_list()
        logger.info("Preloaded %d stocks into cache at startup", len(stocks_list))
    except Exception as e:
        logger.warning("Failed to preload stock list: %s", e)
    yield
    # Graceful shutdown: signal SSE streams to close, then stop scheduler
    logger.info("Initiating graceful shutdown...")
    signal_sse_shutdown()
    stop_scheduler()


app = FastAPI(title="The Wealth API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MetricsMiddleware)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):  # type: ignore[type-arg]
    """Assign a unique request_id to each incoming request."""
    request_id = generate_request_id()
    set_request_id(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth.router)
v1_router.include_router(alerts.router)
v1_router.include_router(portfolios.router)
v1_router.include_router(portfolio_export.router)
v1_router.include_router(stocks.router)
v1_router.include_router(dashboard.router)
v1_router.include_router(users.router)
v1_router.include_router(sync.router)
v1_router.include_router(chart.router)
v1_router.include_router(prices.router)
v1_router.include_router(analytics.router)
v1_router.include_router(watchlist.router)
v1_router.include_router(notifications.router)
v1_router.include_router(health.router)
v1_router.include_router(internal.router)


@v1_router.get("/health")
async def health_check_v1(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Health check under /api/v1/health.

    Returns service status and last DB backup information.
    Response shape:
    {
      "status": "ok",
      "last_backup_at": "2026-03-20T02:00:00+00:00",  # ISO-8601 or null
      "backup_age_hours": 7.5                          # float or null
    }
    """
    backup_info = await get_last_backup_info(db)
    return {"status": "ok", **backup_info}


app.include_router(v1_router)


def _error_body(code: str, message: str) -> dict:
    """Build standardized error response envelope."""
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": get_request_id(),
        }
    }


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(
            code=str(exc.status_code),
            message=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    message = first_error.get("msg", "Validation error")
    return JSONResponse(
        status_code=422,
        content=_error_body(code="422", message=message),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content=_error_body(code="500", message="Internal server error"),
    )


@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check() -> dict:
    return {"status": "ok"}
