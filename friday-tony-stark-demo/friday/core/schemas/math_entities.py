from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class EmotionState:
    emotion_vector: dict[str, float] = field(default_factory=dict)
    session_mood: dict[str, float] = field(default_factory=dict)
    user_style_projection: dict[str, float] = field(default_factory=dict)
    fused_state: dict[str, float] = field(default_factory=dict)
    entropy: float = 0.0
