from __future__ import annotations

from collections.abc import Callable
from threading import RLock

from friday.app.neural_visual.schemas import NeuralVisualAction


NeuralVisualSubscriber = Callable[[NeuralVisualAction], None]


class NeuralVisualCommandBus:
    def __init__(self) -> None:
        self._lock = RLock()
        self._subscribers: list[NeuralVisualSubscriber] = []

    def subscribe(self, subscriber: NeuralVisualSubscriber) -> Callable[[], None]:
        with self._lock:
            if subscriber not in self._subscribers:
                self._subscribers.append(subscriber)

        def unsubscribe() -> None:
            with self._lock:
                if subscriber in self._subscribers:
                    self._subscribers.remove(subscriber)

        return unsubscribe

    def dispatch(self, action: NeuralVisualAction) -> bool:
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


_COMMAND_BUS = NeuralVisualCommandBus()


def get_neural_visual_command_bus() -> NeuralVisualCommandBus:
    return _COMMAND_BUS
