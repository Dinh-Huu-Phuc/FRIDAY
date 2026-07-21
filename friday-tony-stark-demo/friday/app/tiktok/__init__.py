"""TikTok social platform package for FRIDAY."""

from friday.app.tiktok.config.settings import TikTokSettings
from friday.app.tiktok.dependencies import get_tiktok_service, get_tiktok_settings
from friday.app.tiktok.service.service import TikTokService

__all__ = [
    "TikTokService",
    "TikTokSettings",
    "get_tiktok_service",
    "get_tiktok_settings",
]
