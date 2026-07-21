from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SystemSocketSettings:
    path: str = "/system-socket"
    heartbeat_seconds: int = 30
    max_json_bytes: int = 64 * 1024
