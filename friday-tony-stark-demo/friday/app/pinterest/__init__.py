"""Pinterest social platform package for FRIDAY."""

from friday.app.pinterest.config.settings import PinterestSettings
from friday.app.pinterest.dependencies import get_pinterest_service, get_pinterest_settings
from friday.app.pinterest.service.service import PinterestService

__all__ = [
    "PinterestService",
    "PinterestSettings",
    "get_pinterest_service",
    "get_pinterest_settings",
]
