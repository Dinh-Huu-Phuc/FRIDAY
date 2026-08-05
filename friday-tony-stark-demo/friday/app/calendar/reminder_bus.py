from __future__ import annotations

import threading
from collections.abc import Callable

from friday.app.calendar.schemas import CalendarReminderEvent

CalendarReminderSubscriber = Callable[[CalendarReminderEvent], None]


class CalendarReminderBus:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: list[CalendarReminderSubscriber] = []

    def subscribe(
        self,
        subscriber: CalendarReminderSubscriber,
    ) -> Callable[[], None]:
        with self._lock:
            self._subscribers.append(subscriber)

        def unsubscribe() -> None:
            with self._lock:
                if subscriber in self._subscribers:
                    self._subscribers.remove(subscriber)

        return unsubscribe

    def dispatch(self, event: CalendarReminderEvent) -> bool:
        with self._lock:
            subscribers = tuple(self._subscribers)
        delivered = False
        for subscriber in subscribers:
            try:
                subscriber(event)
                delivered = True
            except RuntimeError:
                continue
        return delivered


_REMINDER_BUS = CalendarReminderBus()


def get_calendar_reminder_bus() -> CalendarReminderBus:
    return _REMINDER_BUS
