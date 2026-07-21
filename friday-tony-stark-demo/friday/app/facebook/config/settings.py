"""Settings model for the Facebook package."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from friday.app.common.env import get_env_value
from friday.app.facebook.constants import (
    APP_SECRET_ENV,
    BASE_URL,
    DEFAULT_RETRY_COUNT,
    DEFAULT_TIMEOUT_SECONDS,
    PAGE_ACCESS_TOKEN_ENV,
    PAGE_ID_ENV,
    PLATFORM_ALIASES,
    PLATFORM_NAME,
    VERIFY_TOKEN_ENV,
    WEBHOOK_OBJECT,
    WEBHOOK_STORE_PATH_ENV,
    WEBSITE_URL,
    WEBSITE_URL_ENV,
)

DEFAULT_WEBHOOK_STORE_PATH = Path(__file__).resolve().parents[1] / "facebook_webhook_store.json"


@dataclass(slots=True, frozen=True)
class FacebookSettings:
    platform_name: str = PLATFORM_NAME
    aliases: tuple[str, ...] = PLATFORM_ALIASES
    base_url: str = BASE_URL
    website_url: str = WEBSITE_URL
    website_url_env: str = WEBSITE_URL_ENV
    page_access_token: str = ""
    app_secret: str = ""
    verify_token: str = ""
    page_id: str = ""
    webhook_object: str = WEBHOOK_OBJECT
    webhook_store_path: Path = DEFAULT_WEBHOOK_STORE_PATH
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    retry_count: int = DEFAULT_RETRY_COUNT

    @classmethod
    def from_env(cls) -> "FacebookSettings":
        store_path = Path(
            get_env_value(
                WEBHOOK_STORE_PATH_ENV,
                str(DEFAULT_WEBHOOK_STORE_PATH),
            )
        )
        return cls(
            website_url=get_env_value(WEBSITE_URL_ENV, WEBSITE_URL),
            page_access_token=get_env_value(PAGE_ACCESS_TOKEN_ENV, ""),
            app_secret=get_env_value(APP_SECRET_ENV, ""),
            verify_token=get_env_value(VERIFY_TOKEN_ENV, ""),
            page_id=get_env_value(PAGE_ID_ENV, ""),
            webhook_store_path=store_path,
        )

    @property
    def webhook_enabled(self) -> bool:
        return bool(self.verify_token.strip())
