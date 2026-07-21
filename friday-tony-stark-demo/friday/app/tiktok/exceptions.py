"""Custom exceptions for TikTok integrations."""

class TikTokError(Exception):
    """Base exception for the TikTok module."""


class TikTokConfigurationError(TikTokError):
    """Raised when the TikTok configuration is invalid."""


class TikTokOpenHomepageError(TikTokError):
    """Raised when the TikTok homepage cannot be opened."""
