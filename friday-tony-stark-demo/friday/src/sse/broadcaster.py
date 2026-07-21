from __future__ import annotations

from typing import Any

from friday.src.sse.channels import SseChannel
from friday.src.sse.events import SseEvent
from friday.src.sse.manager import sse_manager


async def publish_event(channel: SseChannel, event: str, data: dict[str, Any]) -> None:
    await sse_manager.publish(channel, SseEvent(event=event, data=data))
