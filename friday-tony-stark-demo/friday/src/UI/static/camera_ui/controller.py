from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, Signal

from friday.app.perception.window import (
    CameraWindowAction,
    get_camera_window_command_bus,
)
from friday.src.UI.static.camera_ui.window import CameraWindow


class CameraWindowController(QObject):
    action_requested = Signal(str)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        window_factory: Callable[[], CameraWindow] = CameraWindow,
    ) -> None:
        super().__init__(parent)
        self._window_factory = window_factory
        self._window: CameraWindow | None = None
        self._subscriber = lambda action: self.action_requested.emit(action.value)
        self._unsubscribe = get_camera_window_command_bus().subscribe(self._subscriber)
        self.action_requested.connect(
            self._apply_action,
            Qt.ConnectionType.QueuedConnection,
        )

    @property
    def window(self) -> CameraWindow | None:
        return self._window

    def open_window(self) -> None:
        if self._window is None:
            self._window = self._window_factory()
            self._window.closed.connect(self._on_window_closed)
        self._window.showNormal()
        self._window.raise_()
        self._window.activateWindow()
        self._window.start_preview()

    def close_window(self) -> None:
        if self._window is not None:
            self._window.close()

    def shutdown(self) -> None:
        self._unsubscribe()
        self.close_window()

    def _apply_action(self, value: str) -> None:
        action = CameraWindowAction(value)
        if action == CameraWindowAction.OPEN:
            self.open_window()
        elif action == CameraWindowAction.CLOSE:
            self.close_window()

    def _on_window_closed(self) -> None:
        self._window = None
