from __future__ import annotations

import asyncio

from fastapi import WebSocket, WebSocketDisconnect

from friday.app.spatial.constants import MAX_STREAM_FPS, MIN_STREAM_FPS
from friday.app.spatial.service.service import SpatialService


class SpatialSocketStreamer:
    def __init__(self, service: SpatialService) -> None:
        self._service = service

    async def stream(self, websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                state = self._service.status()
                fps = max(MIN_STREAM_FPS, min(MAX_STREAM_FPS, state.fps))
                event = self._service.next_event() if state.enabled else self._service.idle_event(state)
                await websocket.send_json(event.model_dump())
                await asyncio.sleep(1 / fps)
        except WebSocketDisconnect:
            return
        except RuntimeError:
            return
