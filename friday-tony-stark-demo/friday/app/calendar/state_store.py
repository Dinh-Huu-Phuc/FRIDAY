from __future__ import annotations

import json
import threading
from pathlib import Path
from uuid import uuid4


class CalendarStateStore:
    def __init__(self, path: Path, *, history_limit: int = 512) -> None:
        self.path = path
        self.history_limit = max(32, history_limit)
        self._lock = threading.RLock()
        self._delivered: list[str] | None = None

    def was_delivered(self, delivery_key: str) -> bool:
        with self._lock:
            return delivery_key in self._load()

    def mark_delivered(self, delivery_key: str) -> None:
        with self._lock:
            delivered = self._load()
            if delivery_key in delivered:
                return
            delivered.append(delivery_key)
            self._delivered = delivered[-self.history_limit :]
            self._write()

    def _load(self) -> list[str]:
        if self._delivered is not None:
            return self._delivered
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            raw_deliveries = payload.get("delivered", [])
            self._delivered = [
                str(item)
                for item in raw_deliveries
                if isinstance(item, str) and item
            ][-self.history_limit :]
        except (OSError, ValueError, TypeError):
            self._delivered = []
        return self._delivered

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(
            f".{self.path.name}.{uuid4().hex}.tmp"
        )
        temporary.write_text(
            json.dumps({"delivered": self._delivered or []}, indent=2),
            encoding="utf-8",
        )
        try:
            temporary.replace(self.path)
        finally:
            temporary.unlink(missing_ok=True)
