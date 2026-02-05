from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Always load the backend-local `.env` regardless of where uvicorn is started from.
    # (Common Windows pitfall: running from repo root means ".env" won't be found.)
    _ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    APP_NAME: str = "InterviewPrep"
    ENV: str = "dev"
    FRONTEND_ORIGINS: str = ""
    FRONTEND_URL: str | None = None

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    DATABASE_URL: str

    DEEPSEEK_API_KEY: str | None = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_TIMEOUT_SECONDS: int = 45
    DEEPSEEK_MAX_RETRIES: int = 2
    DEEPSEEK_RETRY_BACKOFF_SECONDS: float = 0.8

    # Email (optional; dev prints emails to console if not set)
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None
    SMTP_TLS: bool = True
    SENDGRID_API_KEY: str | None = None
    FROM_EMAIL: str | None = None


settings = Settings()
