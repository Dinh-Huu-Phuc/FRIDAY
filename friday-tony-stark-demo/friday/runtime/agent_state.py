from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RuntimeAgentState:
    user_id: str | None = None
    session_id: str | None = None
    current_language: str = "vi"
    session_mood: dict[str, float] = field(default_factory=dict)
    user_style_vector: list[float] = field(default_factory=list)
    user_style_projection: dict[str, float] = field(default_factory=dict)
