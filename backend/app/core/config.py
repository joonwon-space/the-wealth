from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/the_wealth"
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENCRYPTION_MASTER_KEY: str = "change-me-32-bytes-placeholder00"
    REDIS_URL: str = "redis://localhost:6379"
    KIS_APP_KEY: str = ""
    KIS_APP_SECRET: str = ""
    KIS_BASE_URL: str = "https://openapi.koreainvestment.com:9443"
    KIS_ACCOUNT_NO: str = ""
    KIS_ACNT_PRDT_CD: str = "01"


settings = Settings()
