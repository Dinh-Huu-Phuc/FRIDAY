from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class SseEvent:
    event: str
    data: dict[str, Any]
    id: str | None = None
    retry: int | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def encode(self) -> str:
        lines: list[str] = []
        if self.id is not None:
            lines.append(f"id: {self.id}")
        if self.retry is not None:
            lines.append(f"retry: {self.retry}")
        lines.append(f"event: {self.event}")
        payload = {"created_at": self.created_at, **self.data}
        lines.append(f"data: {json.dumps(payload, ensure_ascii=False)}")
        return "\n".join(lines) + "\n\n"
