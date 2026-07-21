"""X social platform package for FRIDAY."""

from friday.app.x.config.settings import XSettings
from friday.app.x.dependencies import get_x_service, get_x_settings
from friday.app.x.service.service import XService

__all__ = [
    "XService",
    "XSettings",
    "get_x_service",
    "get_x_settings",
]
