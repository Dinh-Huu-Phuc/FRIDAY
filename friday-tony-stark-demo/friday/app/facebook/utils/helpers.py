"""Helper functions used by the Facebook package."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Sequence
from typing import Any, Mapping


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


def coerce_timestamp_ms(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def serialize_payload(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def build_signature(app_secret: str, payload_bytes: bytes) -> str:
    digest = hmac.new(
        app_secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def is_valid_signature(
    *,
    app_secret: str,
    payload_bytes: bytes,
    signature: str,
) -> bool:
    expected = build_signature(app_secret, payload_bytes)
    return hmac.compare_digest(expected, str(signature or "").strip())


def classify_messaging_event(event: Mapping[str, Any]) -> str:
    if event.get("message"):
        return "message"
    if event.get("postback"):
        return "postback"
    if event.get("reaction"):
        return "reaction"
    if event.get("delivery"):
        return "delivery"
    if event.get("read"):
        return "read"
    if event.get("optin"):
        return "optin"
    return "messaging_event"


def classify_change_event(change: Mapping[str, Any]) -> str:
    field_name = str(change.get("field") or "change").strip().lower() or "change"
    value = change.get("value")
    if isinstance(value, Mapping):
        item_name = str(value.get("item") or value.get("verb") or "update").strip().lower()
    else:
        item_name = "update"
    cleaned_field = normalize_identifier(field_name).replace("-", "_")
    cleaned_item = normalize_identifier(item_name).replace("-", "_")
    return f"{cleaned_field}:{cleaned_item}"


def build_event_description(payload: Mapping[str, Any]) -> str:
    message_payload = payload.get("message")
    if isinstance(message_payload, Mapping):
        text_value = str(message_payload.get("text") or "").strip()
        if text_value:
            return text_value

    postback_payload = payload.get("postback")
    if isinstance(postback_payload, Mapping):
        title = str(postback_payload.get("title") or "").strip()
        value = str(postback_payload.get("payload") or "").strip()
        if title or value:
            return title or value

    for key in ("reaction", "delivery", "read", "optin"):
        event_value = payload.get(key)
        if isinstance(event_value, Mapping):
            value = str(event_value.get("action") or event_value.get("watermark") or key).strip()
            if value:
                return value

    return str(payload.get("field") or payload.get("verb") or payload.get("item") or "").strip()
