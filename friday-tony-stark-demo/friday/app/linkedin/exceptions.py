"""Custom exceptions for LinkedIn integrations."""

class LinkedInError(Exception):
    """Base exception for the LinkedIn module."""


class LinkedInConfigurationError(LinkedInError):
    """Raised when the LinkedIn configuration is invalid."""


class LinkedInOpenHomepageError(LinkedInError):
    """Raised when the LinkedIn homepage cannot be opened."""
