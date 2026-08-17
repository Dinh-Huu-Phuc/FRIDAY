from __future__ import annotations

from collections.abc import Callable
from threading import RLock

from friday.app.perception.window.schemas import CameraWindowAction

CameraWindowSubscriber = Callable[[CameraWindowAction], None]


class CameraWindowCommandBus:
    def __init__(self) -> None:
        self._lock = RLock()
        self._subscribers: list[CameraWindowSubscriber] = []

    def subscribe(self, subscriber: CameraWindowSubscriber) -> Callable[[], None]:
        with self._lock:
            if subscriber not in self._subscribers:
                self._subscribers.append(subscriber)

        def unsubscribe() -> None:
            with self._lock:
                if subscriber in self._subscribers:
                    self._subscribers.remove(subscriber)

        return unsubscribe

    def dispatch(self, action: CameraWindowAction) -> bool:
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


_COMMAND_BUS = CameraWindowCommandBus()


def get_camera_window_command_bus() -> CameraWindowCommandBus:
    return _COMMAND_BUS
