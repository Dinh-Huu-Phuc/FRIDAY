from __future__ import annotations

from friday.app.neural_visual.command_bus import get_neural_visual_command_bus
from friday.app.neural_visual.intents import match_neural_visual_intent
from friday.app.neural_visual.schemas import (
    NeuralVisualAction,
    NeuralVisualCommandResult,
)


def handle_neural_visual_message(message: str) -> NeuralVisualCommandResult:
    match = match_neural_visual_intent(message)
    if match.action == NeuralVisualAction.NONE:
        return NeuralVisualCommandResult(handled=False)

    accepted = get_neural_visual_command_bus().dispatch(match.action)
    if not accepted:
        return NeuralVisualCommandResult(
            handled=True,
            action=match.action,
            message=(
                "The Neural Network view is available when the FRIDAY desktop "
                "interface is running, Boss."
            ),
        )

    message_text = (
        "Opening the Neural Network, Boss."
        if match.action == NeuralVisualAction.OPEN
        else "Closing the Neural Network, Boss."
    )
    return NeuralVisualCommandResult(
        handled=True,
        accepted=True,
        action=match.action,
        message=message_text,
    )
