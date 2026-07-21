"""Instagram social platform package for FRIDAY."""

from friday.app.instagram.config.settings import InstagramSettings
from friday.app.instagram.dependencies import get_instagram_service, get_instagram_settings
from friday.app.instagram.service.service import InstagramService

__all__ = [
    "InstagramService",
    "InstagramSettings",
    "get_instagram_service",
    "get_instagram_settings",
]
