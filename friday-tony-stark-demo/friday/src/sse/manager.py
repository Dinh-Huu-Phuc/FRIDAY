from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator

from friday.src.sse.channels import SseChannel
from friday.src.sse.events import SseEvent
from friday.src.sse.settings import SseSettings


class SseManager:
    def __init__(self, settings: SseSettings | None = None) -> None:
        self.settings = settings or SseSettings()
        self._subscribers: dict[str, set[asyncio.Queue[SseEvent]]] = defaultdict(set)

    async def subscribe(self, channel: SseChannel) -> AsyncIterator[SseEvent]:
        queue: asyncio.Queue[SseEvent] = asyncio.Queue(maxsize=self.settings.queue_max_size)
        self._subscribers[channel].add(queue)
        try:
            yield SseEvent(event="connected", data={"channel": channel})
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=self.settings.heartbeat_interval_seconds)
                    yield event
                except TimeoutError:
                    yield SseEvent(event="heartbeat", data={"channel": channel})
        finally:
            self._subscribers[channel].discard(queue)

    async def publish(self, channel: SseChannel, event: SseEvent) -> None:
        for queue in list(self._subscribers[channel]):
            if queue.full():
                continue
            await queue.put(event)


sse_manager = SseManager()
