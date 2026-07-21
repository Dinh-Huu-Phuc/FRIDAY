from __future__ import annotations

from dataclasses import dataclass

from friday.app.realtime.system_socket_broadcaster import SystemSocketBroadcaster
from friday.app.realtime.system_socket_events import SystemSocketEvent

from .system_socket_event_bus import SystemSocketEventBus


@dataclass(slots=True)
class WebSocketEventSubscriber:
    broadcaster: SystemSocketBroadcaster

    async def handle(self, event: SystemSocketEvent) -> None:
        await self.broadcaster.manager.broadcast(event)


def attach_websocket_broadcaster(event_bus: SystemSocketEventBus, broadcaster: SystemSocketBroadcaster) -> None:
    subscriber = WebSocketEventSubscriber(broadcaster=broadcaster)
    event_bus.subscribe("*", subscriber.handle)
