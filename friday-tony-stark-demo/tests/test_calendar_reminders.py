from __future__ import annotations

from datetime import datetime, time
from pathlib import Path

import pytest

from friday.app.calendar.markdown_loader import (
    CalendarMarkdownError,
    load_calendar_entries,
    parse_calendar_markdown,
)
from friday.app.calendar.reminder_bus import CalendarReminderBus
from friday.app.calendar.reminder_formatter import format_calendar_reminder
from friday.app.calendar.scheduler import CalendarScheduler
from friday.app.calendar.schemas import CalendarEntry, CalendarReminderEvent
from friday.app.calendar.service import CalendarService
from friday.app.calendar.settings import CalendarSettings
from friday.app.neural_visual.topology import (
    NEURAL_EDGE_MAP,
    NEURAL_NODE_MAP,
    NeuralNodeId,
)
from friday.app.power.service import PowerSnapshot

HEALTHY_CALENDAR = (
    Path(__file__).resolve().parents[1]
    / "friday"
    / "docs"
    / "calendar"
    / "healthy.md"
)


def _settings(tmp_path: Path, source_path: Path) -> CalendarSettings:
    return CalendarSettings(
        enabled=True,
        source_path=source_path,
        state_path=tmp_path / "calendar-state.json",
        timezone_name="UTC",
        poll_interval_seconds=0.1,
        reload_interval_seconds=1.0,
        misfire_grace_seconds=120,
        display_when_active=True,
        voice_enabled=True,
        voice_when_sleeping=True,
        audio_target="desktop",
    )


def _entry() -> CalendarEntry:
    return CalendarEntry(
        entry_id="workdays:06:30:wake-up",
        scope="workdays",
        weekdays=(0, 1, 2, 3, 4),
        start_time=time(6, 30),
        end_time=None,
        title="Wake Up",
        details=("Drink water.",),
        source_line=10,
    )


def test_healthy_markdown_loads_all_timed_sections() -> None:
    entries = load_calendar_entries(HEALTHY_CALENDAR)

    assert len(entries) == 52
    assert sum(entry.scope == "workdays" for entry in entries) == 22
    assert sum(entry.scope == "saturday" for entry in entries) == 14
    assert sum(entry.scope == "sunday" for entry in entries) == 16
    assert entries[0].title == "Wake Up"
    assert entries[0].weekdays == (0, 1, 2, 3, 4)


def test_parser_rejects_untimed_heading_inside_day_section() -> None:
    with pytest.raises(CalendarMarkdownError, match="timed calendar heading"):
        parse_calendar_markdown(
            "# Monday to Friday - Workdays\n"
            "## Morning Routine\n"
            "- Drink water.\n"
        )


def test_reminder_formatter_is_short_and_speech_ready() -> None:
    message = format_calendar_reminder(_entry())

    assert message == "Boss, it is 6:30 AM. Wake Up. Drink water."
    assert len(message) <= 260


def test_scheduler_dispatches_once_and_persists_deduplication(
    tmp_path: Path,
) -> None:
    source = tmp_path / "calendar.md"
    source.write_text(
        "# Monday to Friday - Workdays\n"
        "## 06:30 - Wake Up\n"
        "- Drink water.\n",
        encoding="utf-8",
    )
    settings = _settings(tmp_path, source)
    received: list[tuple[CalendarEntry, datetime]] = []
    scheduler = CalendarScheduler(
        settings,
        lambda entry, scheduled: received.append((entry, scheduled)),
    )
    scheduler.reload_schedule(force=True)
    monday = datetime.fromisoformat("2026-07-27T06:30:00+00:00")

    assert len(scheduler.run_pending(monday)) == 1
    assert scheduler.run_pending(monday) == ()
    assert len(received) == 1

    restarted = CalendarScheduler(
        settings,
        lambda entry, scheduled: received.append((entry, scheduled)),
    )
    restarted.reload_schedule(force=True)
    assert restarted.run_pending(monday) == ()
    assert len(received) == 1


def test_scheduler_delivers_recent_misfire_but_not_old_entries(
    tmp_path: Path,
) -> None:
    source = tmp_path / "calendar.md"
    source.write_text(
        "# Monday to Friday - Workdays\n"
        "## 06:30 - Wake Up\n"
        "- Drink water.\n",
        encoding="utf-8",
    )
    received: list[str] = []
    recent = CalendarScheduler(
        _settings(tmp_path, source),
        lambda entry, _scheduled: received.append(entry.entry_id),
    )
    recent.reload_schedule(force=True)
    recent.run_pending(datetime.fromisoformat("2026-07-27T06:29:00+00:00"))

    assert len(
        recent.run_pending(
            datetime.fromisoformat("2026-07-27T06:31:00+00:00")
        )
    ) == 1
    assert len(received) == 1

    old_settings = _settings(tmp_path / "old", source)
    old = CalendarScheduler(
        old_settings,
        lambda entry, _scheduled: received.append(entry.entry_id),
    )
    old.reload_schedule(force=True)
    old.run_pending(datetime.fromisoformat("2026-07-28T06:29:00+00:00"))
    assert (
        old.run_pending(
            datetime.fromisoformat("2026-07-28T07:00:00+00:00")
        )
        == ()
    )
    assert len(received) == 1


def test_scheduler_keeps_running_when_calendar_is_temporarily_missing(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path, tmp_path / "missing-calendar.md")
    scheduler = CalendarScheduler(settings, lambda *_args: None)

    assert scheduler.start()
    assert scheduler.running

    scheduler.stop()
    assert not scheduler.running


def test_sleeping_reminder_is_voice_only_and_keeps_power_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bus = CalendarReminderBus()
    received: list[CalendarReminderEvent] = []
    bus.subscribe(received.append)
    source = tmp_path / "calendar.md"
    source.write_text("# Monday to Friday - Workdays\n", encoding="utf-8")
    settings = _settings(tmp_path, source)
    sleeping = PowerSnapshot(
        state="sleeping",
        changed_at="2026-07-27T06:00:00+00:00",
        source="test",
    )
    monkeypatch.setattr(
        "friday.app.calendar.service.get_power_state",
        lambda: sleeping,
    )
    monkeypatch.setattr(
        "friday.app.calendar.service.get_agent_console_service",
        lambda: pytest.fail("A sleeping reminder must not write to chat."),
    )
    service = CalendarService(settings, reminder_bus=bus)

    service._on_due(
        _entry(),
        datetime.fromisoformat("2026-07-27T06:30:00+00:00"),
    )

    assert len(received) == 1
    assert received[0].sleeping
    assert received[0].message is None
    assert received[0].audio_target == "desktop"
    assert sleeping.state == "sleeping"


def test_active_reminder_is_written_to_conversation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bus = CalendarReminderBus()
    received: list[CalendarReminderEvent] = []
    bus.subscribe(received.append)
    source = tmp_path / "calendar.md"
    source.write_text("# Monday to Friday - Workdays\n", encoding="utf-8")
    settings = _settings(tmp_path, source)
    monkeypatch.setattr(
        "friday.app.calendar.service.get_power_state",
        lambda: PowerSnapshot(
            state="active",
            changed_at="2026-07-27T06:00:00+00:00",
            source="test",
        ),
    )

    class FakeConsole:
        def add_assistant_message(self, **kwargs) -> dict:
            return {
                "messages": [
                    {
                        "id": "assistant-calendar",
                        "role": "assistant",
                        "content": kwargs["content"],
                        "channel": kwargs["channel"],
                        "status": "received",
                    }
                ]
            }

    monkeypatch.setattr(
        "friday.app.calendar.service.get_agent_console_service",
        lambda: FakeConsole(),
    )
    service = CalendarService(settings, reminder_bus=bus)

    service._on_due(
        _entry(),
        datetime.fromisoformat("2026-07-27T06:30:00+00:00"),
    )

    assert received[0].message is not None
    assert received[0].message["id"] == "assistant-calendar"
    assert not received[0].sleeping


def test_calendar_has_valid_neural_visual_routes() -> None:
    assert NeuralNodeId.CALENDAR in NEURAL_NODE_MAP
    assert (
        f"{NeuralNodeId.CALENDAR}->{NeuralNodeId.RESPONSE}"
        in NEURAL_EDGE_MAP
    )
    assert (
        f"{NeuralNodeId.RESPONSE}->{NeuralNodeId.TTS}"
        in NEURAL_EDGE_MAP
    )
