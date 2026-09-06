from __future__ import annotations

from collections import deque
from uuid import uuid4

from friday.app.perception.world.schemas import (
    WorldEvent,
    WorldEventType,
    WorldModelConfig,
)


class WorldEventJournal:
    """Meaningful transitions only; in-memory and owned by WorldModel's lock."""

    def __init__(self, config: WorldModelConfig) -> None:
        self._retention = config.event_retention_seconds
        self._events: deque[WorldEvent] = deque(maxlen=config.maximum_events)

    def append(
        self,
        event_type: WorldEventType,
        *,
        entity_id: str,
        occurred_at: float,
        description: str,
        confidence: float,
        source_event_id: str | None = None,
    ) -> None:
        self._events.append(
            WorldEvent(
                event_id=uuid4().hex,
                event_type=event_type,
                entity_id=entity_id,
                occurred_at=occurred_at,
                description=description[:320],
                confidence=confidence,
                source_event_id=source_event_id,
            )
        )
        self.prune(occurred_at)

    def prune(self, now: float) -> None:
        while self._events and now - self._events[0].occurred_at > self._retention:
            self._events.popleft()

    def recent(self, *, now: float, limit: int | None = None) -> tuple[WorldEvent, ...]:
        self.prune(now)
        events = tuple(self._events)
        if limit is None:
            return events
        return events[-limit:] if limit > 0 else ()

    def reset(self) -> None:
        self._events.clear()
