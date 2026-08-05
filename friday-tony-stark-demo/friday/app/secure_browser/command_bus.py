from __future__ import annotations

from collections.abc import Callable
from threading import RLock

from friday.app.secure_browser.schemas import SecureBrowserRequest


SecureBrowserSubscriber = Callable[[SecureBrowserRequest], None]


class SecureBrowserCommandBus:
    def __init__(self) -> None:
        self._lock = RLock()
        self._subscribers: list[SecureBrowserSubscriber] = []

    def subscribe(
        self,
        subscriber: SecureBrowserSubscriber,
    ) -> Callable[[], None]:
        with self._lock:
            if subscriber not in self._subscribers:
                self._subscribers.append(subscriber)

        def unsubscribe() -> None:
            with self._lock:
                if subscriber in self._subscribers:
                    self._subscribers.remove(subscriber)

        return unsubscribe

    def dispatch(self, request: SecureBrowserRequest) -> bool:
        with self._lock:
            subscribers = tuple(self._subscribers)
        accepted = False
        for subscriber in subscribers:
            try:
                subscriber(request)
                accepted = True
            except RuntimeError:
                continue
        return accepted


_COMMAND_BUS = SecureBrowserCommandBus()


def get_secure_browser_command_bus() -> SecureBrowserCommandBus:
    return _COMMAND_BUS
