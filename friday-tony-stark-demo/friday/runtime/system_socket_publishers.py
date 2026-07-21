from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from friday.app.realtime.system_socket_channels import SystemSocketChannel
from friday.app.realtime.system_socket_events import SystemSocketEvent

from .system_socket_event_bus import SystemSocketEventBus
from .system_socket_event_types import SystemSocketEventType


@dataclass(slots=True)
class RuntimeSystemSocketPublisher:
    event_bus: SystemSocketEventBus

    async def publish(
        self,
        event_type: SystemSocketEventType | str,
        *,
        channel: SystemSocketChannel | str = SystemSocketChannel.RUNTIME,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self.event_bus.publish(
            SystemSocketEvent(
                type=str(event_type),
                channel=str(channel),
                payload=payload or {},
            )
        )
