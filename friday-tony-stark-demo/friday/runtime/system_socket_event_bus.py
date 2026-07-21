from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from friday.app.realtime.system_socket_events import SystemSocketEvent


SystemSocketSubscriber = Callable[[SystemSocketEvent], Awaitable[None]]


@dataclass(slots=True)
class SystemSocketEventBus:
    subscribers: dict[str, list[SystemSocketSubscriber]] = field(default_factory=lambda: defaultdict(list))

    def subscribe(self, channel: str, callback: SystemSocketSubscriber) -> None:
        self.subscribers[channel].append(callback)

    async def publish(self, event: SystemSocketEvent) -> None:
        callbacks = list(self.subscribers.get(event.channel, [])) + list(self.subscribers.get("*", []))
        for callback in callbacks:
            await callback(event)
