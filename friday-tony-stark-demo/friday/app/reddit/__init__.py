"""Reddit social platform package for FRIDAY."""

from friday.app.reddit.config.settings import RedditSettings
from friday.app.reddit.dependencies import get_reddit_service, get_reddit_settings
from friday.app.reddit.service.service import RedditService

__all__ = [
    "RedditService",
    "RedditSettings",
    "get_reddit_service",
    "get_reddit_settings",
]
