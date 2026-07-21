"""Custom exceptions for Discord integrations."""

class DiscordError(Exception):
    """Base exception for the Discord module."""


class DiscordConfigurationError(DiscordError):
    """Raised when the Discord configuration is invalid."""


class DiscordOpenHomepageError(DiscordError):
    """Raised when the Discord homepage cannot be opened."""
