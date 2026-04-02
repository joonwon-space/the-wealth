from pydantic import ConfigDict, model_validator
from pydantic_settings import BaseSettings

_PLACEHOLDER_SECRETS = {"change-me", "change-me-32-bytes-placeholder00"}


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

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
