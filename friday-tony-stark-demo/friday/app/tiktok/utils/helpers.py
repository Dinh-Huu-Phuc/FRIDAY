"""Helper functions used by the TikTok package."""

from __future__ import annotations

import re
from collections.abc import Sequence


def normalize_identifier(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]+", "-", str(value or "").strip())
    normalized = cleaned.strip("-").lower()
    return normalized or "default"


def build_resource_url(website_url: str, resource_name: str, resource_id: str) -> str:
    base = website_url.rstrip("/")
    return f"{base}/{resource_name.strip('/')}/{normalize_identifier(resource_id)}"


def matches_platform_command(command: str, aliases: Sequence[str]) -> bool:
    normalized = re.sub(r"[^a-z0-9\s]+", " ", str(command or "").strip().lower())
    tokens = set(normalized.split())
    for alias in aliases:
        normalized_alias = re.sub(r"[^a-z0-9\s]+", " ", str(alias).strip().lower())
        if not normalized_alias:
            continue
        if " " in normalized_alias and normalized_alias in normalized:
            return True
        if normalized_alias in tokens:
            return True
    return False
