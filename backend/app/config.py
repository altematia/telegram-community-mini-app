from functools import lru_cache

from pydantic import AnyHttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    app_name: str = "ClosedClub API"
    environment: str = "production"
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: SecretStr
    telegram_bot_token: SecretStr
    telegram_webhook_secret: SecretStr
    telegram_web_app_url: AnyHttpUrl
    telegram_auth_max_age_seconds: int = 86_400

    @field_validator("telegram_webhook_secret")
    @classmethod
    def validate_webhook_secret(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        allowed = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
        )
        if not 32 <= len(secret) <= 256 or any(char not in allowed for char in secret):
            raise ValueError(
                "TELEGRAM_WEBHOOK_SECRET must be 32-256 URL-safe characters"
            )
        return value

    @field_validator("telegram_web_app_url")
    @classmethod
    def require_https_web_app(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.scheme != "https":
            raise ValueError("TELEGRAM_WEB_APP_URL must use HTTPS")
        return value

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    model_config = SettingsConfigDict(
        env_file=None,
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
