from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .system_socket_channels import DEFAULT_SYSTEM_SOCKET_CHANNELS
from .system_socket_manager import SystemSocketManager
from .system_socket_settings import SystemSocketSettings


def parse_channels(raw: str | None) -> set[str]:
    if not raw:
        return set(DEFAULT_SYSTEM_SOCKET_CHANNELS)
    requested = {item.strip() for item in raw.split(",") if item.strip()}
    allowed = set(DEFAULT_SYSTEM_SOCKET_CHANNELS)
    return requested & allowed or allowed


def create_system_socket_router(
    manager: SystemSocketManager | None = None,
    settings: SystemSocketSettings | None = None,
) -> APIRouter:
    manager = manager or SystemSocketManager()
    settings = settings or SystemSocketSettings()
    router = APIRouter()

    @router.websocket(settings.path)
    async def system_socket_endpoint(websocket: WebSocket) -> None:
        connection_id = uuid4().hex
        channels = parse_channels(websocket.query_params.get("channels"))
        await manager.connect(connection_id, websocket, channels)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(connection_id)

    return router
