from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from friday.app.secure_browser.navigation import FRIDAY_HOME_URL


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ICON_PATH = PROJECT_ROOT / "friday" / "assets" / "img" / "Friday.jpg"


def _default_profile_path() -> Path:
    configured_root = os.getenv("LOCALAPPDATA", "").strip()
    root = Path(configured_root) if configured_root else Path.home() / ".friday"
    return root / "FRIDAY" / "Browser" / "User Data"


@dataclass(frozen=True, slots=True)
class SecureBrowserSettings:
    enabled: bool
    home_url: str
    profile_path: Path
    icon_path: Path


def _valid_web_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def get_secure_browser_settings() -> SecureBrowserSettings:
    configured_home = os.getenv(
        "FRIDAY_SECURE_BROWSER_HOME_URL",
        FRIDAY_HOME_URL,
    ).strip()
    home_url = (
        configured_home
        if configured_home == FRIDAY_HOME_URL or _valid_web_url(configured_home)
        else FRIDAY_HOME_URL
    )

    configured_profile = os.getenv(
        "FRIDAY_SECURE_BROWSER_PROFILE_PATH",
        "",
    ).strip()
    profile_path = (
        Path(configured_profile).expanduser()
        if configured_profile
        else _default_profile_path()
    )
    if not profile_path.is_absolute():
        profile_path = PROJECT_ROOT / profile_path

    configured_icon = os.getenv("FRIDAY_SECURE_BROWSER_ICON", "").strip()
    icon_path = (
        Path(configured_icon).expanduser()
        if configured_icon
        else DEFAULT_ICON_PATH
    )
    if not icon_path.is_absolute():
        icon_path = PROJECT_ROOT / icon_path

    return SecureBrowserSettings(
        enabled=os.getenv("FRIDAY_SECURE_BROWSER_ENABLED", "true").lower()
        in {"1", "true", "yes", "on"},
        home_url=home_url,
        profile_path=profile_path.resolve(),
        icon_path=icon_path.resolve(),
    )
