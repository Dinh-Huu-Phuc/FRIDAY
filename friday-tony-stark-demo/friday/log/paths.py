from __future__ import annotations

import os
from pathlib import Path


FRIDAY_PACKAGE_DIR = Path(__file__).resolve().parents[1]
FRIDAY_LOG_DIR = Path(os.getenv("FRIDAY_LOG_DIR", str(FRIDAY_PACKAGE_DIR / "log"))).expanduser()
FRIDAY_SAVE_LOG_DIR = FRIDAY_LOG_DIR / "saveLog"


def friday_log_dir(*parts: str) -> Path:
    return FRIDAY_LOG_DIR.joinpath(*parts)


def friday_save_log_dir(*parts: str) -> Path:
    return FRIDAY_SAVE_LOG_DIR.joinpath(*parts)
