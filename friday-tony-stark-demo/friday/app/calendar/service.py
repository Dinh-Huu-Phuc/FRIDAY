from __future__ import annotations

import logging
import threading
from datetime import datetime

from friday.app.agent_console.service import get_agent_console_service
from friday.app.calendar.reminder_bus import (
    CalendarReminderBus,
    get_calendar_reminder_bus,
)
from friday.app.calendar.reminder_formatter import format_calendar_reminder
from friday.app.calendar.scheduler import CalendarScheduler
from friday.app.calendar.schemas import CalendarEntry, CalendarReminderEvent
from friday.app.calendar.settings import CalendarSettings
from friday.app.neural_visual import (
    NeuralEventStatus,
    NeuralNodeId,
    emit_neural_activity,
    emit_neural_transfer,
    new_neural_trace_id,
)
from friday.app.power import get_power_state

_CALENDAR_SESSION_ID = "python-ui"
logger = logging.getLogger(__name__)


class CalendarService:
    def __init__(
        self,
        settings: CalendarSettings | None = None,
        *,
        reminder_bus: CalendarReminderBus | None = None,
    ) -> None:
        self.settings = settings or CalendarSettings()
        self.reminder_bus = reminder_bus or get_calendar_reminder_bus()
        self.scheduler = CalendarScheduler(
            self.settings,
            self._on_due,
        )

    def start(self) -> bool:
        return self.scheduler.start()

    def stop(self) -> None:
        self.scheduler.stop()

    def _on_due(self, entry: CalendarEntry, scheduled_at: datetime) -> None:
        power_snapshot = get_power_state()
        triggered_at = datetime.now(self.settings.timezone)
        trace_id = new_neural_trace_id()
        spoken_text = format_calendar_reminder(entry)
        audio_target = self.settings.resolved_audio_target
        if power_snapshot.sleeping and not self.settings.voice_when_sleeping:
            audio_target = "none"

        emit_neural_activity(
            NeuralNodeId.CALENDAR,
            trace_id=trace_id,
            event_type="calendar.reminder.due",
            summary=f"{entry.title} at {scheduled_at:%H:%M}",
        )
        emit_neural_transfer(
            NeuralNodeId.CALENDAR,
            NeuralNodeId.RESPONSE,
            trace_id=trace_id,
            event_type="calendar.reminder.prepared",
            summary=spoken_text,
            status=NeuralEventStatus.SUCCESS,
        )

        message: dict[str, object] | None = None
        if not power_snapshot.sleeping and self.settings.display_when_active:
            try:
                snapshot = get_agent_console_service().add_assistant_message(
                    session_id=_CALENDAR_SESSION_ID,
                    content=spoken_text,
                    channel="voice",
                )
                messages = list(snapshot.get("messages") or [])
                if messages:
                    message = dict(messages[-1])
                emit_neural_transfer(
                    NeuralNodeId.RESPONSE,
                    NeuralNodeId.UI,
                    trace_id=trace_id,
                    event_type="calendar.reminder.displayed",
                    summary=spoken_text,
                    status=NeuralEventStatus.SUCCESS,
                )
            except Exception:
                logger.exception(
                    "Calendar reminder could not be added to the UI"
                )

        if audio_target != "none":
            emit_neural_transfer(
                NeuralNodeId.RESPONSE,
                NeuralNodeId.TTS,
                trace_id=trace_id,
                event_type="calendar.reminder.audio.queued",
                summary=spoken_text,
            )

        self.reminder_bus.dispatch(
            CalendarReminderEvent(
                entry_id=entry.entry_id,
                title=entry.title,
                spoken_text=spoken_text,
                scheduled_at=scheduled_at,
                triggered_at=triggered_at,
                power_state=power_snapshot.state,
                trace_id=trace_id,
                audio_target=audio_target,
                message=message,
            )
        )


_SERVICE_LOCK = threading.Lock()
_SERVICE: CalendarService | None = None


def get_calendar_service() -> CalendarService:
    global _SERVICE
    with _SERVICE_LOCK:
        if _SERVICE is None:
            _SERVICE = CalendarService()
        return _SERVICE
