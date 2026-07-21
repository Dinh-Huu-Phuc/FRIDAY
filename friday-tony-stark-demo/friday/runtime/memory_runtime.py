from __future__ import annotations

from dataclasses import dataclass, field

from .agent_state import RuntimeAgentState


@dataclass(slots=True)
class RuntimeMemory:
    sessions: dict[str, RuntimeAgentState] = field(default_factory=dict)

    def get_or_create(self, session_id: str) -> RuntimeAgentState:
        if session_id not in self.sessions:
            self.sessions[session_id] = RuntimeAgentState(session_id=session_id)
        return self.sessions[session_id]
