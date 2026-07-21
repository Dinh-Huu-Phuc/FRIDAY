from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import WebSocket

from .system_socket_channels import DEFAULT_SYSTEM_SOCKET_CHANNELS
from .system_socket_events import SystemSocketEvent


@dataclass(slots=True)
class SystemSocketConnection:
    websocket: WebSocket
    channels: set[str] = field(default_factory=set)


@dataclass(slots=True)
class SystemSocketManager:
    connections: dict[str, SystemSocketConnection] = field(default_factory=dict)
    channel_index: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    async def connect(self, connection_id: str, websocket: WebSocket, channels: set[str] | None = None) -> None:
        await websocket.accept()
        selected = channels or set(DEFAULT_SYSTEM_SOCKET_CHANNELS)
        self.connections[connection_id] = SystemSocketConnection(websocket=websocket, channels=selected)
        for channel in selected:
            self.channel_index[channel].add(connection_id)

    def disconnect(self, connection_id: str) -> None:
        connection = self.connections.pop(connection_id, None)
        if connection is None:
            return
        for channel in connection.channels:
            self.channel_index[channel].discard(connection_id)

    async def send(self, connection_id: str, event: SystemSocketEvent) -> None:
        connection = self.connections.get(connection_id)
        if connection is None:
            return
        await connection.websocket.send_json(event.to_dict())

    async def broadcast(self, event: SystemSocketEvent) -> None:
        stale: list[str] = []
        for connection_id in list(self.channel_index.get(event.channel, set())):
            try:
                await self.send(connection_id, event)
            except Exception:
                stale.append(connection_id)
        for connection_id in stale:
            self.disconnect(connection_id)
