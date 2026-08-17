from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from friday.app.code_map import (
    CodeMapAction,
    CodeMapCommandBus,
    CodeMapSettings,
    get_code_map_command_bus,
    handle_code_map_message,
    match_code_map_intent,
)
from friday.src.UI.static.code_map_ui.controller import CodeMapWindowController


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


class _FakeCodeMapWindow(QObject):
    closed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.show_count = 0
        self.raise_count = 0
        self.activate_count = 0
        self.close_count = 0

    def showNormal(self) -> None:
        self.show_count += 1

    def raise_(self) -> None:
        self.raise_count += 1

    def activateWindow(self) -> None:
        self.activate_count += 1

    def close(self) -> None:
        self.close_count += 1
        self.closed.emit()


def test_code_map_intents_are_flexible_but_bounded() -> None:
    open_samples = (
        "FRIDAY, open code map!",
        "Friday open the code map",
        "Please open code map",
        "Friday, could you please show the Code Map?",
        "Hey Friday launch codemap for me",
    )
    close_samples = (
        "Friday close the code map",
        "Could you hide code map please?",
        "FRIDAY dismiss the codemap",
    )
    for sample in open_samples:
        assert match_code_map_intent(sample).action == CodeMapAction.OPEN
    for sample in close_samples:
        assert match_code_map_intent(sample).action == CodeMapAction.CLOSE

    assert match_code_map_intent("open code map in Chrome").action == CodeMapAction.NONE
    assert match_code_map_intent("explain the code map").action == CodeMapAction.NONE
    assert match_code_map_intent("open code mapping guide").action == CodeMapAction.NONE


def test_command_bus_dispatches_and_unsubscribes() -> None:
    bus = CodeMapCommandBus()
    received: list[CodeMapAction] = []
    unsubscribe = bus.subscribe(received.append)

    assert bus.dispatch(CodeMapAction.OPEN)
    unsubscribe()
    assert not bus.dispatch(CodeMapAction.CLOSE)
    assert received == [CodeMapAction.OPEN]


def test_service_dispatches_to_a_running_desktop(monkeypatch) -> None:
    received: list[CodeMapAction] = []
    unsubscribe = get_code_map_command_bus().subscribe(received.append)
    monkeypatch.setattr(
        "friday.app.code_map.service.get_code_map_settings",
        lambda: CodeMapSettings(
            True,
            "https://grapuco.com/dashboard",
            Path(__file__).parent,
        ),
    )
    try:
        result = handle_code_map_message("FRIDAY open code map")
    finally:
        unsubscribe()

    assert result.handled
    assert result.accepted
    assert result.action == CodeMapAction.OPEN
    assert received == [CodeMapAction.OPEN]


def test_controller_keeps_one_window_and_closes_it_from_the_bus() -> None:
    app = _app()
    windows: list[_FakeCodeMapWindow] = []

    def build_window() -> _FakeCodeMapWindow:
        window = _FakeCodeMapWindow()
        windows.append(window)
        return window

    controller = CodeMapWindowController(window_factory=build_window)
    try:
        bus = get_code_map_command_bus()
        assert bus.dispatch(CodeMapAction.OPEN)
        app.processEvents()
        assert len(windows) == 1
        assert windows[0].show_count == 1

        assert bus.dispatch(CodeMapAction.OPEN)
        app.processEvents()
        assert len(windows) == 1
        assert windows[0].show_count == 2

        assert bus.dispatch(CodeMapAction.CLOSE)
        app.processEvents()
        assert windows[0].close_count == 1
        assert controller.window is None
    finally:
        controller.shutdown()

    assert not get_code_map_command_bus().dispatch(CodeMapAction.OPEN)
