"""Lightweight JSON store for Facebook webhook events."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from friday.app.facebook.exceptions import FacebookWebhookStorageError


class FacebookWebhookStore:
    """Persist webhook-derived messages and notifications for FRIDAY."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def append(
        self,
        *,
        messages: list[dict[str, Any]],
        notifications: list[dict[str, Any]],
        events: list[dict[str, Any]],
    ) -> None:
        payload = self._read_payload()
        payload["messages"] = self._merge_items(payload["messages"], messages)
        payload["notifications"] = self._merge_items(payload["notifications"], notifications)
        payload["events"] = self._merge_items(payload["events"], events)
        self._write_payload(payload)

    def list_messages(
        self,
        *,
        limit: int,
        unread_only: bool = False,
        sender_id: str = "",
    ) -> list[dict[str, Any]]:
        payload = self._read_payload()
        sender_filter = str(sender_id or "").strip()
        items = [
            item
            for item in payload["messages"]
            if (not sender_filter or str(item.get("sender_id") or "").strip() == sender_filter)
            and (not unread_only or not bool((item.get("metadata") or {}).get("is_read")))
        ]
        items.sort(key=lambda item: int(item.get("timestamp_ms") or 0), reverse=True)
        return items[: max(1, limit)]

    def list_notifications(
        self,
        *,
        limit: int,
        event_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        payload = self._read_payload()
        normalized_event_types = {str(item).strip().lower() for item in (event_types or []) if str(item).strip()}
        items = [
            item
            for item in payload["notifications"]
            if not normalized_event_types
            or str(item.get("event_type") or "").strip().lower() in normalized_event_types
        ]
        items.sort(key=lambda item: int(item.get("timestamp_ms") or 0), reverse=True)
        return items[: max(1, limit)]

    def _read_payload(self) -> dict[str, list[dict[str, Any]]]:
        with self._lock:
            if not self.path.exists():
                return self._empty_payload()
            try:
                raw_content = self.path.read_text(encoding="utf-8").strip()
                if not raw_content:
                    return self._empty_payload()
                payload = json.loads(raw_content)
                return {
                    "messages": list(payload.get("messages") or []),
                    "notifications": list(payload.get("notifications") or []),
                    "events": list(payload.get("events") or []),
                }
            except (OSError, json.JSONDecodeError) as exc:
                raise FacebookWebhookStorageError(
                    f"Unable to load Facebook webhook store from {self.path}."
                ) from exc

    def _write_payload(self, payload: dict[str, list[dict[str, Any]]]) -> None:
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except OSError as exc:
                raise FacebookWebhookStorageError(
                    f"Unable to write Facebook webhook store to {self.path}."
                ) from exc

    @staticmethod
    def _empty_payload() -> dict[str, list[dict[str, Any]]]:
        return {
            "messages": [],
            "notifications": [],
            "events": [],
        }

    @staticmethod
    def _merge_items(
        existing: list[dict[str, Any]],
        incoming: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for item in existing + incoming:
            item_id = str(item.get("id") or "").strip()
            if not item_id:
                continue
            merged[item_id] = item
        values = list(merged.values())
        values.sort(key=lambda item: int(item.get("timestamp_ms") or 0), reverse=True)
        return values
