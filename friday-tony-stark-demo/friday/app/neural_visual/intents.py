from __future__ import annotations

import re

from friday.app.neural_visual.schemas import (
    NeuralVisualAction,
    NeuralVisualIntentMatch,
)


_PHRASES = {
    "open neural network": (NeuralVisualAction.OPEN, "open_default"),
    "friday open neural network": (NeuralVisualAction.OPEN, "open_friday"),
    "show neural network": (NeuralVisualAction.OPEN, "show_default"),
    "friday show neural network": (NeuralVisualAction.OPEN, "show_friday"),
    "switch to neural network": (NeuralVisualAction.OPEN, "switch_default"),
    "friday switch to neural network": (NeuralVisualAction.OPEN, "switch_friday"),
    "close neural network": (NeuralVisualAction.CLOSE, "close_default"),
    "friday close neural network": (NeuralVisualAction.CLOSE, "close_friday"),
    "hide neural network": (NeuralVisualAction.CLOSE, "hide_default"),
    "friday hide neural network": (NeuralVisualAction.CLOSE, "hide_friday"),
    "friday close the neural network": (NeuralVisualAction.CLOSE, "close_the_network"),
}


def normalize_neural_visual_phrase(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def match_neural_visual_intent(message: str) -> NeuralVisualIntentMatch:
    matched = _PHRASES.get(normalize_neural_visual_phrase(message))
    if matched is None:
        return NeuralVisualIntentMatch()
    action, trigger_id = matched
    return NeuralVisualIntentMatch(action=action, trigger_id=trigger_id)
