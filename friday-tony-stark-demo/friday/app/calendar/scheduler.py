from __future__ import annotations

import logging
import threading
import time as time_module
from collections.abc import Callable
from datetime import datetime, timedelta

from friday.app.calendar.markdown_loader import load_calendar_entries
from friday.app.calendar.schemas import CalendarEntry
from friday.app.calendar.settings import CalendarSettings
from friday.app.calendar.state_store import CalendarStateStore

CalendarDueCallback = Callable[[CalendarEntry, datetime], None]
logger = logging.getLogger(__name__)


class CalendarScheduler:
    def __init__(
        self,
        settings: CalendarSettings,
        on_due: CalendarDueCallback,
        *,
        state_store: CalendarStateStore | None = None,
    ) -> None:
        self.settings = settings
        self.on_due = on_due
        self.state_store = state_store or CalendarStateStore(settings.state_path)
        self._entries: tuple[CalendarEntry, ...] = ()
        self._source_mtime_ns = -1
        self._last_checked_minute: datetime | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()

    @property
    def entries(self) -> tuple[CalendarEntry, ...]:
        with self._lock:
            return self._entries

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        if not self.settings.enabled or self.running:
            return False
        self._stop_event.clear()
        try:
            self.reload_schedule(force=True)
        except Exception:
            logger.exception(
                "Calendar schedule could not be loaded; it will be retried"
            )
        self._thread = threading.Thread(
            target=self._run,
            name="friday-calendar-scheduler",
            daemon=True,
        )
        self._thread.start()
        return True

    def stop(self, timeout: float = 3.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)
        self._thread = None

    def reload_schedule(self, *, force: bool = False) -> int:
        source = self.settings.source_path
        source_mtime_ns = source.stat().st_mtime_ns
        if not force and source_mtime_ns == self._source_mtime_ns:
            return len(self.entries)
        entries = load_calendar_entries(source)
        with self._lock:
            self._entries = entries
            self._source_mtime_ns = source_mtime_ns
        return len(entries)

    def run_pending(self, now: datetime | None = None) -> tuple[str, ...]:
        current = (now or datetime.now(self.settings.timezone)).astimezone(
            self.settings.timezone
        )
        current_minute = current.replace(second=0, microsecond=0)
        candidates = self._candidate_minutes(current_minute)
        delivered: list[str] = []
        entries = self.entries
        for scheduled_at in candidates:
            for entry in entries:
                if not entry.is_due(scheduled_at):
                    continue
                delivery_key = (
                    f"{entry.entry_id}@"
                    f"{scheduled_at.isoformat(timespec='minutes')}"
                )
                if self.state_store.was_delivered(delivery_key):
                    continue
                self.on_due(entry, scheduled_at)
                self.state_store.mark_delivered(delivery_key)
                delivered.append(delivery_key)
        return tuple(delivered)

    def _candidate_minutes(self, current: datetime) -> tuple[datetime, ...]:
        previous = self._last_checked_minute
        self._last_checked_minute = current
        if previous is None or current < previous:
            return (current,)
        if current == previous:
            return ()
        elapsed_seconds = (current - previous).total_seconds()
        if elapsed_seconds > self.settings.misfire_grace_seconds:
            return (current,)
        candidates: list[datetime] = []
        cursor = previous + timedelta(minutes=1)
        while cursor <= current:
            candidates.append(cursor)
            cursor += timedelta(minutes=1)
        return tuple(candidates)

    def _run(self) -> None:
        next_reload_at = 0.0
        while not self._stop_event.is_set():
            monotonic_now = time_module.monotonic()
            if monotonic_now >= next_reload_at:
                next_reload_at = (
                    monotonic_now + self.settings.reload_interval_seconds
                )
                try:
                    self.reload_schedule()
                except Exception:
                    logger.exception("Calendar schedule reload failed")
            try:
                self.run_pending()
            except Exception:
                logger.exception("Calendar scheduler tick failed")
            self._stop_event.wait(self.settings.poll_interval_seconds)
