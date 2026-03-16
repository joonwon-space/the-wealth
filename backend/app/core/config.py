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
