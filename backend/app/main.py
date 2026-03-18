from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import alerts, analytics, auth, chart, dashboard, portfolio_export, portfolios, prices, stocks, sync, users, watchlist
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import configure_logging, generate_request_id, get_logger, set_request_id
from app.core.middleware import SecurityHeadersMiddleware
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.stock_search import _load_stock_list

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    start_scheduler()
    # Preload KRX + ETF stock list into Redis cache at startup
    try:
        stocks = await _load_stock_list()
        logger.info("Preloaded %d stocks into cache at startup", len(stocks))
    except Exception as e:
        logger.warning("Failed to preload stock list: %s", e)
    yield
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


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):  # type: ignore[type-arg]
    """Assign a unique request_id to each incoming request."""
    request_id = generate_request_id()
    set_request_id(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(auth.router)
app.include_router(alerts.router)
app.include_router(portfolios.router)
app.include_router(portfolio_export.router)
app.include_router(stocks.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(sync.router)
app.include_router(chart.router)
app.include_router(prices.router)
app.include_router(analytics.router)
app.include_router(watchlist.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
