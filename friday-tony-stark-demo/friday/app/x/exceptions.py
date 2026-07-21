"""Custom exceptions for X integrations."""

class XError(Exception):
    """Base exception for the X module."""


class XConfigurationError(XError):
    """Raised when the X configuration is invalid."""


class XOpenHomepageError(XError):
    """Raised when the X homepage cannot be opened."""
