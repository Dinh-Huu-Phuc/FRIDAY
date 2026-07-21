"""
Application configuration loaded from environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class Config:
    SERVER_NAME: str = os.getenv("SERVER_NAME", "Friday")
    DEBUG: bool = _get_bool("DEBUG", False)

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    SEARCH_API_KEY: str = os.getenv("SEARCH_API_KEY", "")

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    STT_REFINER_ENABLED: bool = _get_bool("STT_REFINER_ENABLED", True)
    STT_REFINER_PROVIDER: str = os.getenv("STT_REFINER_PROVIDER", "groq").strip().lower()
    STT_REFINER_TIMEOUT: float = _get_float("STT_REFINER_TIMEOUT", 4.0)

    BATCH_TRAINING_ENABLED: bool = _get_bool("BATCH_TRAINING_ENABLED", True)
    BATCH_TRAINING_CHECK_INTERVAL_SEC: int = _get_int("BATCH_TRAINING_CHECK_INTERVAL_SEC", 300)
    BATCH_TRAINING_DAILY_TIME_UTC: str = os.getenv("BATCH_TRAINING_DAILY_TIME_UTC", "02:00")
    BATCH_TRAINING_MIN_PENDING_SAMPLES: int = _get_int("BATCH_TRAINING_MIN_PENDING_SAMPLES", 50)

    NEWSDATA_API_KEY: str = os.getenv("NEWSDATA_API_KEY", "")
    WORLD_NEWS: str = os.getenv("WORLD_NEWS", "")
    NEWS_DEFAULT_LANGUAGE: str = os.getenv("NEWS_DEFAULT_LANGUAGE", "en").strip().lower() or "en"
    NEWS_DEFAULT_COUNTRY: str = os.getenv("NEWS_DEFAULT_COUNTRY", "vn").strip().lower() or "vn"
    NEWS_DEFAULT_LIMIT: int = _get_int("NEWS_DEFAULT_LIMIT", 6)
    NEWS_REQUEST_TIMEOUT: float = _get_float("NEWS_REQUEST_TIMEOUT", 8.0)


config = Config()
