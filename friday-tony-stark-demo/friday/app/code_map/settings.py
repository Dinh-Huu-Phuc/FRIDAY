from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CODE_MAP_URL = "https://grapuco.com/dashboard"
DEFAULT_PROFILE_PATH = PROJECT_ROOT / "friday" / "log" / "runtime" / "code_map_profile"


@dataclass(frozen=True, slots=True)
class CodeMapSettings:
    enabled: bool
    url: str
    profile_path: Path


def _valid_web_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def get_code_map_settings() -> CodeMapSettings:
    configured_url = os.getenv("FRIDAY_CODE_MAP_URL", DEFAULT_CODE_MAP_URL).strip()
    url = configured_url if _valid_web_url(configured_url) else DEFAULT_CODE_MAP_URL
    configured_profile = os.getenv("FRIDAY_CODE_MAP_PROFILE_PATH", "").strip()
    profile_path = Path(configured_profile).expanduser() if configured_profile else DEFAULT_PROFILE_PATH
    if not profile_path.is_absolute():
        profile_path = PROJECT_ROOT / profile_path
    return CodeMapSettings(
        enabled=os.getenv("FRIDAY_CODE_MAP_ENABLED", "true").lower()
        in {"1", "true", "yes", "on"},
        url=url,
        profile_path=profile_path.resolve(),
    )
