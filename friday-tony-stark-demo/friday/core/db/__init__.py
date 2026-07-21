"""Lazy public API for FRIDAY core database features.

Keeping this package initializer free of eager imports lets Alembic load models
without also starting application services that depend on those same models.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORTS = {
    "CoreAccessCredential": ("friday.core.db.models", "CoreAccessCredential"),
    "ScreenCaptureAsset": ("friday.core.db.models", "ScreenCaptureAsset"),
    "ScreenCaptureRecord": ("friday.core.db.models", "ScreenCaptureRecord"),
    "CoreCredentialStore": (
        "friday.core.db.repositories",
        "CoreCredentialStore",
    ),
    "CredentialAlreadyConfiguredError": (
        "friday.core.db.repositories",
        "CredentialAlreadyConfiguredError",
    ),
    "ScreenCaptureRepository": (
        "friday.core.db.repositories",
        "ScreenCaptureRepository",
    ),
    "CoreAccessGate": ("friday.core.db.services", "CoreAccessGate"),
    "InvalidPasswordError": (
        "friday.core.db.services",
        "InvalidPasswordError",
    ),
    "PasswordConfirmationError": (
        "friday.core.db.services",
        "PasswordConfirmationError",
    ),
    "get_core_access_gate": (
        "friday.core.db.services",
        "get_core_access_gate",
    ),
    "ScreenshotArchiveResult": (
        "friday.core.db.services",
        "ScreenshotArchiveResult",
    ),
    "ScreenshotArchiveService": (
        "friday.core.db.services",
        "ScreenshotArchiveService",
    ),
    "SupabaseStorageClient": (
        "friday.core.db.services",
        "SupabaseStorageClient",
    ),
    "screenshot_cloud_enabled": (
        "friday.core.db.services",
        "screenshot_cloud_enabled",
    ),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
