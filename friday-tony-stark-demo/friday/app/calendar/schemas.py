from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Any, Literal

CalendarAudioTarget = Literal["desktop", "web", "all", "none"]


@dataclass(frozen=True, slots=True)
class CalendarEntry:
    entry_id: str
    scope: str
    weekdays: tuple[int, ...]
    start_time: time
    end_time: time | None
    title: str
    details: tuple[str, ...]
    source_line: int

    def is_due(self, value: datetime) -> bool:
        return (
            value.weekday() in self.weekdays
            and value.hour == self.start_time.hour
            and value.minute == self.start_time.minute
        )


@dataclass(frozen=True, slots=True)
class CalendarReminderEvent:
    entry_id: str
    title: str
    spoken_text: str
    scheduled_at: datetime
    triggered_at: datetime
    power_state: str
    trace_id: str
    audio_target: CalendarAudioTarget
    message: dict[str, Any] | None = None

    @property
    def sleeping(self) -> bool:
        return self.power_state == "sleeping"

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "title": self.title,
            "spoken_text": self.spoken_text,
            "scheduled_at": self.scheduled_at.isoformat(),
            "triggered_at": self.triggered_at.isoformat(),
            "power_state": self.power_state,
            "sleeping": self.sleeping,
            "trace_id": self.trace_id,
            "audio_target": self.audio_target,
            "message": self.message,
        }
