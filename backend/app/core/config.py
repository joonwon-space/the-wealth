from pydantic import ConfigDict, model_validator
from pydantic_settings import BaseSettings

_PLACEHOLDER_SECRETS = {"change-me", "change-me-32-bytes-placeholder00"}


class Settings(BaseSettings):
    # extra='ignore' — 운영/로컬 환경에 따라 .env 가 추가 키를 가질 수 있음
    # (e.g. VISUAL_QA_EMAIL/PASSWORD 같은 보조 도구용). 미선언 키는 무시한다.
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/the_wealth"
    )
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENCRYPTION_MASTER_KEY: str = "change-me-32-bytes-placeholder00"
    REDIS_URL: str = "redis://localhost:6379"
    KIS_BASE_URL: str = "https://openapi.koreainvestment.com:9443"
    CORS_ORIGINS: str = "http://localhost:3000"
    # Cookie domain for cross-subdomain auth (e.g. ".joonwon.dev" for prod).
    # Leave empty for localhost dev (domain not set on cookie).
    COOKIE_DOMAIN: str = ""
    # Shared secret used by internal system scripts (e.g. backup-postgres.sh)
    # to authenticate to internal-only API endpoints.
    # Set to a strong random value in production; leave empty to disable the endpoints.
    INTERNAL_SECRET: str = ""

    # Sentry DSN for error tracking. Leave empty to disable.
    SENTRY_DSN: str = ""

    # Deployment environment name sent to Sentry (e.g. "production", "staging", "development").
    ENVIRONMENT: str = "development"

    # File logging (RotatingFileHandler). Leave LOG_DIR empty to disable file logging.
    LOG_DIR: str = ""
    LOG_MAX_BYTES: int = 10_485_760  # 10 MB
    LOG_BACKUP_COUNT: int = 5

    # Cloudflare R2 (S3-compatible) for DB backups. Leave empty to disable.
    R2_ENDPOINT: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = ""

    # KIS API rate limiting (token bucket + concurrency cap).
    # Policy (실전투자): 1초당 18건 per account; /oauth2/tokenP 1초당 1건.
    # BURST + (PER_SEC × 1s) must stay ≤ 18 within any 1-second sliding window.
    #
    # 단계적 상향 history:
    #   Sprint 0: 5/s burst 12 (KIS 정책 28%)
    #   Sprint 3: 8/s burst 16 (KIS 정책 44%)
    #   Sprint 5: 8/s burst 20 (KIS 정책 헤드룸 활용) — 라이브 P95 slow acquire
    #            로그 다수 발견 (dashboard polling + portfolios fanout 시점 겹침)
    #            burst 토큰 4개 추가로 동시 fanout 시 wait 감소.
    KIS_RATE_LIMIT_PER_SEC: float = 8.0
    KIS_RATE_LIMIT_BURST: int = 20
    # Max in-flight KIS HTTP requests at any time (independent of req/sec).
    # Prevents a flat-burst from opening dozens of concurrent TCP connections,
    # which can trigger KIS connection-level rejection (ConnectTimeout) even
    # when the per-second rate is within policy.
    KIS_MAX_CONCURRENCY: int = 6
    # /oauth2/tokenP dedicated limiter (1/s policy).
    KIS_TOKEN_RATE_LIMIT_PER_SEC: float = 1.0
    KIS_TOKEN_RATE_LIMIT_BURST: int = 1
    # 429 / rate-limit-rejection retry: KIS recommends immediate retry.
    KIS_HTTP_MAX_RETRIES: int = 1
    # Network error (ConnectError/TimeoutException) retry for read-only requests.
    KIS_HTTP_NETWORK_RETRY: int = 1
    # When True, rate limiter is bypassed (useful for local dev / tests).
    KIS_MOCK_MODE: bool = False

    # Web Push (VAPID). Empty keys disable push — the /push/* endpoints still
    # respond but no actual notifications are delivered.
    # Generate with: `python -m py_vapid --applicationServerKey`
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    # mailto: or https://... contact for abuse reports (required by spec).
    VAPID_SUBJECT: str = "mailto:admin@joonwon.dev"

    @model_validator(mode="after")
    def reject_placeholder_secrets(self) -> "Settings":
        if self.JWT_SECRET_KEY in _PLACEHOLDER_SECRETS:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a strong random value (not the default placeholder)"
            )
        if self.ENCRYPTION_MASTER_KEY in _PLACEHOLDER_SECRETS:
            raise ValueError(
                "ENCRYPTION_MASTER_KEY must be set to a 64-char hex string (not the default placeholder)"
            )
        if not self.KIS_BASE_URL.startswith("https://"):
            raise ValueError("KIS_BASE_URL must use HTTPS")
        return self


settings = Settings()
