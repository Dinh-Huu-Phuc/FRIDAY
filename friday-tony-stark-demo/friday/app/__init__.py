"""Social application packages and runtime helpers for FRIDAY."""

from friday.app.computer.dependencies import get_computer_service
from friday.app.registry import (
    SOCIAL_PLATFORM_REGISTRY,
    SocialCommand,
    build_social_search_url,
    is_social_open_request,
    parse_social_command,
    resolve_social_platform,
)
from friday.app.runtime import open_social_platform

__all__ = [
    "SOCIAL_PLATFORM_REGISTRY",
    "SocialCommand",
    "build_social_search_url",
    "get_computer_service",
    "is_social_open_request",
    "open_social_platform",
    "parse_social_command",
    "resolve_social_platform",
]
