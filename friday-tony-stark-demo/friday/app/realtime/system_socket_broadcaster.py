from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .system_socket_events import SystemSocketEvent
from .system_socket_manager import SystemSocketManager


@dataclass(slots=True)
class SystemSocketBroadcaster:
    manager: SystemSocketManager

    async def publish(self, event_type: str, *, channel: str, payload: dict[str, Any] | None = None) -> None:
        await self.manager.broadcast(SystemSocketEvent(type=event_type, channel=channel, payload=payload or {}))
