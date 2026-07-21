"""Custom exceptions for Reddit integrations."""

class RedditError(Exception):
    """Base exception for the Reddit module."""


class RedditConfigurationError(RedditError):
    """Raised when the Reddit configuration is invalid."""


class RedditOpenHomepageError(RedditError):
    """Raised when the Reddit homepage cannot be opened."""
