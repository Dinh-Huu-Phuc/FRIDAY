from __future__ import annotations

from collections.abc import Callable
from threading import RLock

from friday.app.code_map.schemas import CodeMapAction


CodeMapSubscriber = Callable[[CodeMapAction], None]


class CodeMapCommandBus:
    def __init__(self) -> None:
        self._lock = RLock()
        self._subscribers: list[CodeMapSubscriber] = []

    def subscribe(self, subscriber: CodeMapSubscriber) -> Callable[[], None]:
        with self._lock:
            if subscriber not in self._subscribers:
                self._subscribers.append(subscriber)

        def unsubscribe() -> None:
            with self._lock:
                if subscriber in self._subscribers:
                    self._subscribers.remove(subscriber)

        return unsubscribe

    def dispatch(self, action: CodeMapAction) -> bool:
        with self._lock:
            subscribers = tuple(self._subscribers)
        accepted = False
        for subscriber in subscribers:
            try:
                subscriber(action)
                accepted = True
            except RuntimeError:
                continue
        return accepted


_COMMAND_BUS = CodeMapCommandBus()


def get_code_map_command_bus() -> CodeMapCommandBus:
    return _COMMAND_BUS
