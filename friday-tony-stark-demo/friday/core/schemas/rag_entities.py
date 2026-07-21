from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Document:
    text: str
    source_path: str
    source_type: str
    title: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    text: str
    source_path: str
    source_type: str
    title: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievedChunk:
    chunk: Chunk
    score: float
    rerank_score: float | None = None
