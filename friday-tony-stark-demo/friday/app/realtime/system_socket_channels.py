from __future__ import annotations

from enum import StrEnum


class SystemSocketChannel(StrEnum):
    AGENT = "agent"
    RUNTIME = "runtime"
    LOGS = "logs"
    RAG = "rag"


DEFAULT_SYSTEM_SOCKET_CHANNELS = tuple(channel.value for channel in SystemSocketChannel)
