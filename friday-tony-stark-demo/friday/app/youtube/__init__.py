"""YouTube social platform package for FRIDAY."""

from friday.app.youtube.config.settings import YouTubeSettings
from friday.app.youtube.dependencies import get_youtube_service, get_youtube_settings
from friday.app.youtube.service.service import YouTubeService

__all__ = [
    "YouTubeService",
    "YouTubeSettings",
    "get_youtube_service",
    "get_youtube_settings",
]
