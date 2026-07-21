from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

from ..math.similarity import cosine_similarity
from ..schemas.rag_entities import Chunk, RetrievedChunk


class VectorStore(Protocol):
    def upsert(self, chunk: Chunk, vector: list[float]) -> None:
        ...

    def query(self, query_vector: list[float], *, top_k: int) -> list[RetrievedChunk]:
        ...

    def dump(self, path: Path) -> None:
        ...

    def load(self, path: Path) -> None:
        ...


@dataclass(slots=True)
class _VectorEntry:
    chunk: Chunk
    vector: list[float]


@dataclass(slots=True)
class InMemoryVectorStore:
    entries: dict[str, _VectorEntry] = field(default_factory=dict)

    def upsert(self, chunk: Chunk, vector: list[float]) -> None:
        self.entries[chunk.chunk_id] = _VectorEntry(chunk=chunk, vector=[float(v) for v in vector])

    def query(self, query_vector: list[float], *, top_k: int) -> list[RetrievedChunk]:
        scored = []
        for entry in self.entries.values():
            score = cosine_similarity(query_vector, entry.vector)
            scored.append(RetrievedChunk(chunk=entry.chunk, score=score))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[: max(1, top_k)]

    def dump(self, path: Path) -> None:
        payload = [
            {
                "chunk": asdict(entry.chunk),
                "vector": entry.vector,
            }
            for entry in self.entries.values()
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.entries.clear()
        for item in raw:
            chunk_payload = dict(item["chunk"])
            chunk = Chunk(
                chunk_id=str(chunk_payload["chunk_id"]),
                text=str(chunk_payload["text"]),
                source_path=str(chunk_payload["source_path"]),
                source_type=str(chunk_payload["source_type"]),
                title=chunk_payload.get("title"),
                metadata={str(k): str(v) for k, v in dict(chunk_payload.get("metadata", {})).items()},
            )
            self.entries[chunk.chunk_id] = _VectorEntry(
                chunk=chunk,
                vector=[float(v) for v in list(item.get("vector", []))],
            )
