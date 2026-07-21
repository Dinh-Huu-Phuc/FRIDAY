from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class VectorDocument:
    id: str
    text: str
    source_path: str
    source_type: str
    title: str | None = None
    tags: list[str] = field(default_factory=list)
    created_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VectorRecord:
    id: str
    chunk_id: str
    text: str
    source_path: str
    source_type: str
    title: str | None = None
    tags: list[str] = field(default_factory=list)
    created_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VectorSearchResult:
    chunk: VectorRecord
    score: float
    rerank_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk": self.chunk.to_dict(),
            "score": self.score,
            "rerank_score": self.rerank_score,
        }
