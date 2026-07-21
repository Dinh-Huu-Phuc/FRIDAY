"""Settings model for the Reddit package."""

from __future__ import annotations

from dataclasses import dataclass

from friday.app.common.env import get_env_value
from friday.app.reddit.constants import (
    BASE_URL,
    DEFAULT_RETRY_COUNT,
    DEFAULT_TIMEOUT_SECONDS,
    PLATFORM_ALIASES,
    PLATFORM_NAME,
    WEBSITE_URL,
    WEBSITE_URL_ENV,
)


@dataclass(slots=True, frozen=True)
class RedditSettings:
    platform_name: str = PLATFORM_NAME
    aliases: tuple[str, ...] = PLATFORM_ALIASES
    base_url: str = BASE_URL
    website_url: str = WEBSITE_URL
    website_url_env: str = WEBSITE_URL_ENV
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    retry_count: int = DEFAULT_RETRY_COUNT

    @classmethod
    def from_env(cls) -> "RedditSettings":
        return cls(website_url=get_env_value(WEBSITE_URL_ENV, WEBSITE_URL))
