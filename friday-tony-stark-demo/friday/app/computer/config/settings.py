"""Settings model for the computer package."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from friday.app.common.env import get_env_value
from friday.app.computer.constants import (
    ALLOW_SHELL_ENV,
    COMMAND_TIMEOUT_ENV,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_IMAGE_QUALITY,
    DEFAULT_MAX_IMAGE_HEIGHT,
    DEFAULT_MAX_IMAGE_WIDTH,
    DEFAULT_MOUSE_DURATION,
    DEFAULT_SAFETY_MODE,
    DEFAULT_TYPE_INTERVAL,
    IMAGE_QUALITY_ENV,
    MAX_IMAGE_HEIGHT_ENV,
    MAX_IMAGE_WIDTH_ENV,
    PLATFORM_NAME,
    SAFETY_MODE_ENV,
    SCREENSHOT_DIR_ENV,
)

DEFAULT_SCREENSHOT_DIR = Path(__file__).resolve().parents[3] / "log" / "image"


def _get_bool(name: str, default: bool) -> bool:
    value = get_env_value(name, str(default))
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name: str, default: int) -> int:
    value = get_env_value(name, str(default))
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(slots=True, frozen=True)
class ComputerSettings:
    platform_name: str = PLATFORM_NAME
    screenshot_dir: Path = DEFAULT_SCREENSHOT_DIR
    image_quality: int = DEFAULT_IMAGE_QUALITY
    max_image_width: int = DEFAULT_MAX_IMAGE_WIDTH
    max_image_height: int = DEFAULT_MAX_IMAGE_HEIGHT
    default_command_timeout: int = DEFAULT_COMMAND_TIMEOUT
    allow_shell: bool = True
    safety_mode: str = DEFAULT_SAFETY_MODE
    mouse_duration: float = DEFAULT_MOUSE_DURATION
    type_interval: float = DEFAULT_TYPE_INTERVAL

    @classmethod
    def from_env(cls) -> "ComputerSettings":
        return cls(
            screenshot_dir=Path(get_env_value(SCREENSHOT_DIR_ENV, str(DEFAULT_SCREENSHOT_DIR))),
            image_quality=_get_int(IMAGE_QUALITY_ENV, DEFAULT_IMAGE_QUALITY),
            max_image_width=_get_int(MAX_IMAGE_WIDTH_ENV, DEFAULT_MAX_IMAGE_WIDTH),
            max_image_height=_get_int(MAX_IMAGE_HEIGHT_ENV, DEFAULT_MAX_IMAGE_HEIGHT),
            default_command_timeout=_get_int(COMMAND_TIMEOUT_ENV, DEFAULT_COMMAND_TIMEOUT),
            allow_shell=_get_bool(ALLOW_SHELL_ENV, True),
            safety_mode=get_env_value(SAFETY_MODE_ENV, DEFAULT_SAFETY_MODE).lower(),
        )
