"""Custom exceptions for Instagram integrations."""

class InstagramError(Exception):
    """Base exception for the Instagram module."""


class InstagramConfigurationError(InstagramError):
    """Raised when the Instagram configuration is invalid."""


class InstagramOpenHomepageError(InstagramError):
    """Raised when the Instagram homepage cannot be opened."""
