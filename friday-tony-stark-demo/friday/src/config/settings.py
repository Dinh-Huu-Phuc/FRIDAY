from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")


def normalize_database_url(value: str) -> str:
    """Return a SQLAlchemy URL that uses Psycopg 3."""
    database_url = value.strip()
    if not database_url:
        return ""
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if not database_url.startswith("postgresql+psycopg://"):
        raise ValueError("DATABASE_URL must be a PostgreSQL connection URL.")
    return database_url


class Settings:
    app_name: str = "FRIDAY REST API"
    api_v1_prefix: str = "/api/v1"
    sse_prefix: str = "/sse"
    environment: str = os.getenv("FRIDAY_ENV", "local")
    host: str = os.getenv("FRIDAY_API_HOST", "127.0.0.1")
    port: int = int(os.getenv("FRIDAY_API_PORT", "8001"))
    access_log: bool = os.getenv("FRIDAY_ACCESS_LOG", "false").lower() in {"1", "true", "yes", "on"}
    local_only: bool = os.getenv("FRIDAY_LOCAL_ONLY", "true").lower() in {"1", "true", "yes", "on"}
    expose_api_docs: bool = os.getenv("FRIDAY_EXPOSE_API_DOCS", "false").lower() in {"1", "true", "yes", "on"}
    auto_open_browser: bool = os.getenv("FRIDAY_AUTO_OPEN_BROWSER", "true").lower() in {"1", "true", "yes", "on"}
    desktop_ui_enabled: bool = os.getenv("FRIDAY_DESKTOP_UI_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    browser_path: str = os.getenv("FRIDAY_BROWSER_PATH", "")
    start_mode: str = os.getenv("FRIDAY_START_MODE", "fast")
    background_warmup: bool = os.getenv("FRIDAY_BACKGROUND_WARMUP", "true").lower() in {"1", "true", "yes", "on"}
    initial_state: str = os.getenv("FRIDAY_INITIAL_STATE", "active")
    local_wake_word: bool = os.getenv("FRIDAY_LOCAL_WAKE_WORD", "true").lower() in {"1", "true", "yes", "on"}
    ollama_preload: bool = os.getenv("FRIDAY_OLLAMA_PRELOAD", "true").lower() in {"1", "true", "yes", "on"}
    window_sleep_enabled: bool = os.getenv("FRIDAY_WINDOW_SLEEP_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    window_snapshot_path: str = os.getenv("FRIDAY_WINDOW_SNAPSHOT_PATH", "")
    window_restore_on_startup: bool = os.getenv("FRIDAY_WINDOW_RESTORE_ON_STARTUP", "true").lower() in {"1", "true", "yes", "on"}
    window_transition_delay_ms: float = float(os.getenv("FRIDAY_WINDOW_TRANSITION_DELAY_MS", "140"))
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "FRIDAY_CORS_ORIGINS",
            "http://localhost:8001,http://127.0.0.1:8001",
        ).split(",")
        if origin.strip()
    ]

    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-env")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    refresh_token_cookie_name: str = os.getenv("REFRESH_TOKEN_COOKIE_NAME", "friday_refresh_token")
    refresh_token_cookie_path: str = os.getenv("REFRESH_TOKEN_COOKIE_PATH", "/api/v1/auth/refresh")
    refresh_token_cookie_samesite: str = os.getenv("REFRESH_TOKEN_COOKIE_SAMESITE", "lax")
    refresh_token_cookie_secure: bool = os.getenv("REFRESH_TOKEN_COOKIE_SECURE", "").lower() in {"1", "true", "yes", "on"}
    friday_api_key_pepper: str = os.getenv("FRIDAY_API_KEY_PEPPER", jwt_secret_key)

    @property
    def database_url(self) -> str:
        return normalize_database_url(os.getenv("DATABASE_URL", ""))


@lru_cache
def get_settings() -> Settings:
    return Settings()
