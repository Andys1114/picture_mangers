"""Application configuration via pydantic-settings."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Values can be overridden via environment variables or a `.env` file at the
    backend/ root. Defaults are tuned for local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./picture_mangers.db"

    # Media storage (relative to backend/ unless absolute)
    media_dir: str = "./media"

    # Auth / sessions
    session_expire_days: int = 30
    # Cookie Secure flag — False for local dev (no HTTPS), True in production.
    secure_cookie: bool = False

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def media_path(self) -> Path:
        p = Path(self.media_dir)
        return p if p.is_absolute() else Path(__file__).resolve().parent.parent / self.media_dir


settings = Settings()
