"""Environment loading utilities for social platform packages."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

APP_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=APP_ENV_PATH, override=False)


def get_env_value(name: str, default: str) -> str:
    value = os.getenv(name, default)
    cleaned = str(value).strip()
    return cleaned or default
