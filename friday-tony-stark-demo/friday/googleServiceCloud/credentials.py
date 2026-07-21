from __future__ import annotations

import os
from pathlib import Path

SERVICE_ACCOUNT_FILENAME = "emerald-ether-479816-v6-e17f7309f6da.json"


def get_bundled_service_account_path() -> Path:
    """Return the bundled Google service-account JSON path inside the repo."""
    return Path(__file__).resolve().with_name(SERVICE_ACCOUNT_FILENAME)


def ensure_google_application_credentials(force: bool = False) -> str | None:
    """
    Populate GOOGLE_APPLICATION_CREDENTIALS from the bundled JSON if needed.

    This is only relevant for Google Cloud SDK/client flows that use
    Application Default Credentials. It does not replace GOOGLE_API_KEY.
    """
    current = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if current and not force and Path(current).expanduser().exists():
        return current

    service_account_path = get_bundled_service_account_path()
    if not service_account_path.exists():
        return current or None

    resolved = str(service_account_path)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = resolved
    return resolved
