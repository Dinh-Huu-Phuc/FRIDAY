from __future__ import annotations

from typing import Literal


SseChannel = Literal["runtime", "agent", "logs", "rag"]
CHANNELS: tuple[SseChannel, ...] = ("runtime", "agent", "logs", "rag")
