"""Custom exceptions for Telegram integrations."""

class TelegramError(Exception):
    """Base exception for the Telegram module."""


class TelegramConfigurationError(TelegramError):
    """Raised when the Telegram configuration is invalid."""


class TelegramOpenHomepageError(TelegramError):
    """Raised when the Telegram homepage cannot be opened."""
