"""Service exports for the Instagram package."""

from friday.app.instagram.service.client import InstagramClient
from friday.app.instagram.service.mapper import InstagramMapper
from friday.app.instagram.service.parser import InstagramParser
from friday.app.instagram.service.service import InstagramService

__all__ = [
    "InstagramClient",
    "InstagramMapper",
    "InstagramParser",
    "InstagramService",
]
