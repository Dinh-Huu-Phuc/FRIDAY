from __future__ import annotations

from types import SimpleNamespace

from friday.app.neural_visual import (
    NeuralVisualAction,
    NeuralVisualCommandBus,
    get_neural_visual_command_bus,
    handle_neural_visual_message,
    match_neural_visual_intent,
)
from friday.src.UI.static.desktop_ui.window import DesktopWindow


def test_neural_visual_intents_are_strict_and_allowlisted() -> None:
    assert (
        match_neural_visual_intent("FRIDAY, open Neural Network!").action
        == NeuralVisualAction.OPEN
    )
    assert (
        match_neural_visual_intent("FRIDAY close Neural Network").action
        == NeuralVisualAction.CLOSE
    )
    assert (
        match_neural_visual_intent("please open the neural network").action
        == NeuralVisualAction.NONE
    )
    assert (
        match_neural_visual_intent("open neural network in Chrome").action
        == NeuralVisualAction.NONE
    )


def test_neural_visual_command_bus_dispatches_and_unsubscribes() -> None:
    bus = NeuralVisualCommandBus()
    received: list[NeuralVisualAction] = []
    unsubscribe = bus.subscribe(received.append)

    assert bus.dispatch(NeuralVisualAction.OPEN)
    unsubscribe()
    assert not bus.dispatch(NeuralVisualAction.CLOSE)
    assert received == [NeuralVisualAction.OPEN]


def test_service_dispatches_neural_visual_to_desktop() -> None:
    received: list[NeuralVisualAction] = []
    unsubscribe = get_neural_visual_command_bus().subscribe(received.append)
    try:
        opened = handle_neural_visual_message("FRIDAY open Neural Network")
        closed = handle_neural_visual_message("FRIDAY close Neural Network")
    finally:
        unsubscribe()

    assert opened.handled and opened.accepted
    assert closed.handled and closed.accepted
    assert received == [NeuralVisualAction.OPEN, NeuralVisualAction.CLOSE]


def test_desktop_action_returns_to_the_previous_visual() -> None:
    selected: list[str] = []
    statuses: list[str] = []
    window = SimpleNamespace(
        settings_panel=SimpleNamespace(select_visual=selected.append),
        _visual_before_neural="video",
        _set_status=statuses.append,
    )

    DesktopWindow._apply_neural_visual_action(window, "open")
    DesktopWindow._apply_neural_visual_action(window, "close")

    assert selected == ["neural", "video"]
    assert statuses == ["Neural Network active", "Neural Network closed"]
