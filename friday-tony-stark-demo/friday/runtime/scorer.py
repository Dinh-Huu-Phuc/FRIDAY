from __future__ import annotations

from dataclasses import dataclass

from ..core.math import entropy, fuse_state, smooth_session_mood


@dataclass(slots=True)
class RuntimeScorer:
    def update_session_mood(
        self,
        previous_mood: dict[str, float],
        current_emotion: dict[str, float],
    ) -> dict[str, float]:
        return smooth_session_mood(previous_mood, current_emotion)

    def compute_entropy(self, emotion_vector: dict[str, float]) -> float:
        return entropy(emotion_vector)

    def compute_fused_state(
        self,
        current_emotion: dict[str, float],
        session_mood: dict[str, float],
        user_style_projection: dict[str, float],
    ) -> dict[str, float]:
        return fuse_state(current_emotion, session_mood, user_style_projection)
