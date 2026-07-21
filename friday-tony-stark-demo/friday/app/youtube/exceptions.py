"""Custom exceptions for YouTube integrations."""

class YouTubeError(Exception):
    """Base exception for the YouTube module."""


class YouTubeConfigurationError(YouTubeError):
    """Raised when the YouTube configuration is invalid."""


class YouTubeOpenHomepageError(YouTubeError):
    """Raised when the YouTube homepage cannot be opened."""
