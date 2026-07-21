"""LinkedIn social platform package for FRIDAY."""

from friday.app.linkedin.config.settings import LinkedInSettings
from friday.app.linkedin.dependencies import get_linkedin_service, get_linkedin_settings
from friday.app.linkedin.service.service import LinkedInService

__all__ = [
    "LinkedInService",
    "LinkedInSettings",
    "get_linkedin_service",
    "get_linkedin_settings",
]
