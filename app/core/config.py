from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings loaded from environment variables."""

    APP_NAME: str = "FastAPI Production Starter"
    APP_ENV: str = "local"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # Read from .env in local development while allowing OS env overrides.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
