from __future__ import annotations

from dataclasses import dataclass, field

from ..core.schemas.rag_entities import RetrievedChunk


@dataclass(slots=True)
class RetrievalContext:
    query: str
    chunks: list[RetrievedChunk] = field(default_factory=list)
    prompt_context: str = ""
