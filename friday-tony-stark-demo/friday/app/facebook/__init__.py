"""Facebook social platform package for FRIDAY."""

from friday.app.facebook.config.settings import FacebookSettings
from friday.app.facebook.dependencies import (
    get_facebook_service,
    get_facebook_settings,
    get_facebook_webhook_store,
)
from friday.app.facebook.service.service import FacebookService

__all__ = [
    "FacebookService",
    "FacebookSettings",
    "get_facebook_service",
    "get_facebook_settings",
    "get_facebook_webhook_store",
]
