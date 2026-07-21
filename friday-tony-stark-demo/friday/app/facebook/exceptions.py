"""Custom exceptions for Facebook integrations."""


class FacebookError(Exception):
    """Base exception for the Facebook module."""


class FacebookConfigurationError(FacebookError):
    """Raised when the Facebook configuration is invalid."""


class FacebookOpenHomepageError(FacebookError):
    """Raised when the Facebook homepage cannot be opened."""


class FacebookWebhookVerificationError(FacebookError):
    """Raised when the incoming Facebook webhook verification fails."""


class FacebookWebhookSignatureError(FacebookError):
    """Raised when a webhook signature is invalid."""


class FacebookWebhookStorageError(FacebookError):
    """Raised when webhook payloads cannot be stored or loaded."""
