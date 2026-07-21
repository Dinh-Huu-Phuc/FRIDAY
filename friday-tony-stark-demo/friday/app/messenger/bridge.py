from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from friday.app.messenger.schemas import MessengerConversationPreview


_RUNTIME_DIR = Path(__file__).resolve().parents[2] / "log" / "runtime"
_COMMAND_PATH = _RUNTIME_DIR / "messenger_bridge_command.json"
_SNAPSHOT_PATH = _RUNTIME_DIR / "messenger_bridge_snapshot.json"


class MessengerExtensionBridge:
    def __init__(
        self,
        *,
        command_path: Path | None = None,
        snapshot_path: Path | None = None,
    ) -> None:
        self.command_path = command_path or _COMMAND_PATH
        self.snapshot_path = snapshot_path or _SNAPSHOT_PATH

    def request_scan(self) -> str:
        request_id = uuid4().hex
        self._write_json(
            self.command_path,
            {
                "request_id": request_id,
                "action": "scan_latest_messenger",
                "status": "pending",
                "created_at": time.time(),
            },
        )
        return request_id

    def pending_command(self, *, max_age_seconds: float = 45.0) -> dict[str, object] | None:
        payload = self._read_json(self.command_path)
        if payload.get("status") != "pending" or payload.get("action") != "scan_latest_messenger":
            return None
        try:
            age = time.time() - float(payload.get("created_at") or 0)
        except (TypeError, ValueError):
            return None
        if age < 0 or age > max_age_seconds:
            return None
        request_id = str(payload.get("request_id") or "").strip()
        if not request_id:
            return None
        return {
            "request_id": request_id,
            "action": "scan_latest_messenger",
            "created_at": payload.get("created_at"),
        }

    def submit_snapshot(
        self,
        *,
        request_id: str,
        conversations: Iterable[dict[str, object]],
        page_url: str = "",
    ) -> bool:
        command = self.pending_command()
        normalized_request_id = str(request_id or "").strip()
        if command is None or command["request_id"] != normalized_request_id:
            return False

        sanitized = [self._sanitize_conversation(item) for item in conversations]
        sanitized = [item for item in sanitized if item is not None][:20]
        self._write_json(
            self.snapshot_path,
            {
                "request_id": normalized_request_id,
                "captured_at": time.time(),
                "page_url": str(page_url or "")[:500],
                "conversations": sanitized,
            },
        )
        self._write_json(
            self.command_path,
            {
                **command,
                "status": "completed",
                "completed_at": time.time(),
            },
        )
        return True

    def wait_for_latest(
        self,
        request_id: str,
        *,
        timeout_seconds: float = 12.0,
        poll_interval: float = 0.2,
    ) -> MessengerConversationPreview | None:
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        while time.monotonic() <= deadline:
            payload = self._read_json(self.snapshot_path)
            if payload.get("request_id") == request_id:
                conversations = payload.get("conversations")
                if not isinstance(conversations, list) or not conversations:
                    return None
                items = [self._to_preview(item) for item in conversations if isinstance(item, dict)]
                items = [item for item in items if item is not None]
                if not items:
                    return None
                return next((item for item in items if item.unread), items[0])
            time.sleep(max(0.05, poll_interval))
        raise TimeoutError("Messenger extension did not return a snapshot in time.")

    @staticmethod
    def _sanitize_conversation(item: dict[str, object]) -> dict[str, object] | None:
        sender = " ".join(str(item.get("sender") or "").split())[:160]
        preview = " ".join(str(item.get("preview") or "").split())[:1000]
        if not sender or not preview:
            return None
        return {
            "sender": sender,
            "preview": preview,
            "timestamp": " ".join(str(item.get("timestamp") or "").split())[:80],
            "unread": bool(item.get("unread")),
            "url": str(item.get("url") or "")[:500],
        }

    @staticmethod
    def _to_preview(item: dict[str, object]) -> MessengerConversationPreview | None:
        sanitized = MessengerExtensionBridge._sanitize_conversation(item)
        if sanitized is None:
            return None
        return MessengerConversationPreview(
            sender=str(sanitized["sender"]),
            preview=str(sanitized["preview"]),
            timestamp=str(sanitized["timestamp"]),
            unread=bool(sanitized["unread"]),
            url=str(sanitized["url"]),
        )

    @staticmethod
    def _read_json(path: Path) -> dict[str, object]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, TypeError, ValueError):
            return {}

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid4().hex}.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        temporary.replace(path)
