"""Custom exceptions for Pinterest integrations."""

class PinterestError(Exception):
    """Base exception for the Pinterest module."""


class PinterestConfigurationError(PinterestError):
    """Raised when the Pinterest configuration is invalid."""


class PinterestOpenHomepageError(PinterestError):
    """Raised when the Pinterest homepage cannot be opened."""
