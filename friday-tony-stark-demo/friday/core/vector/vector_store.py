from __future__ import annotations

import json
import pickle
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .vector_schemas import VectorRecord, VectorSearchResult
from .vector_similarity import cosine_similarity, normalize_vector


class VectorStore(Protocol):
    def upsert(self, chunk: VectorRecord, vector: list[float]) -> None:
        ...

    def delete(self, chunk_id: str) -> None:
        ...

    def query(self, query_vector: list[float], *, top_k: int) -> list[VectorSearchResult]:
        ...

    def dump(self, path: Path) -> None:
        ...

    def load(self, path: Path) -> None:
        ...


@dataclass(slots=True)
class _VectorEntry:
    chunk: VectorRecord
    vector: list[float]


@dataclass(slots=True)
class InMemoryVectorStore:
    entries: dict[str, _VectorEntry] = field(default_factory=dict)

    def upsert(self, chunk: VectorRecord, vector: list[float]) -> None:
        self.entries[chunk.chunk_id] = _VectorEntry(chunk=chunk, vector=normalize_vector([float(v) for v in vector]))

    def delete(self, chunk_id: str) -> None:
        self.entries.pop(chunk_id, None)

    def query(self, query_vector: list[float], *, top_k: int) -> list[VectorSearchResult]:
        query_vector = normalize_vector([float(v) for v in query_vector])
        scored = []
        for entry in self.entries.values():
            score = cosine_similarity(query_vector, entry.vector)
            scored.append(VectorSearchResult(chunk=entry.chunk, score=score))
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
            chunk = record_from_payload(dict(item["chunk"]))
            self.entries[chunk.chunk_id] = _VectorEntry(
                chunk=chunk,
                vector=normalize_vector([float(v) for v in list(item.get("vector", []))]),
            )


def record_from_payload(chunk_payload: dict[str, Any]) -> VectorRecord:
    metadata = dict(chunk_payload.get("metadata", {}))
    return VectorRecord(
        id=str(chunk_payload.get("id") or chunk_payload.get("chunk_id")),
        chunk_id=str(chunk_payload["chunk_id"]),
        text=str(chunk_payload["text"]),
        source_path=str(chunk_payload["source_path"]),
        source_type=str(chunk_payload["source_type"]),
        title=chunk_payload.get("title"),
        tags=[str(item) for item in list(chunk_payload.get("tags", metadata.get("tags", [])) or [])],
        created_at=chunk_payload.get("created_at") or metadata.get("created_at"),
        metadata=metadata,
    )


@dataclass(slots=True)
class FaissVectorStore:
    dimensions: int
    normalize: bool = True
    chunks: dict[str, VectorRecord] = field(default_factory=dict)
    vectors: dict[str, list[float]] = field(default_factory=dict)
    _faiss: Any = field(init=False, repr=False)
    _index: Any = field(init=False, repr=False)
    _chunk_ids: list[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            import faiss  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - depends on optional package
            raise RuntimeError("faiss-cpu is required for FaissVectorStore. Install faiss-cpu or use InMemoryVectorStore.") from exc
        self._faiss = faiss
        self._index = faiss.IndexFlatIP(int(self.dimensions))
        self._chunk_ids = []

    def upsert(self, chunk: VectorRecord, vector: list[float]) -> None:
        vector = [float(value) for value in vector]
        if len(vector) != self.dimensions:
            raise ValueError(f"Expected vector dimension {self.dimensions}, got {len(vector)}")
        self.chunks[chunk.chunk_id] = chunk
        self.vectors[chunk.chunk_id] = normalize_vector(vector) if self.normalize else vector
        self._rebuild_index()

    def delete(self, chunk_id: str) -> None:
        self.chunks.pop(chunk_id, None)
        self.vectors.pop(chunk_id, None)
        self._rebuild_index()

    def query(self, query_vector: list[float], *, top_k: int) -> list[VectorSearchResult]:
        if not self._chunk_ids:
            return []
        import numpy as np

        query = [float(value) for value in query_vector]
        if self.normalize:
            query = normalize_vector(query)
        matrix = np.array([query], dtype="float32")
        scores, indexes = self._index.search(matrix, max(1, min(top_k, len(self._chunk_ids))))
        results: list[VectorSearchResult] = []
        for score, index in zip(scores[0].tolist(), indexes[0].tolist(), strict=False):
            if index < 0:
                continue
            chunk_id = self._chunk_ids[index]
            results.append(VectorSearchResult(chunk=self.chunks[chunk_id], score=float(score)))
        return results

    def dump(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        self._faiss.write_index(self._index, str(path / "index.faiss"))
        (path / "metadata.pkl").write_bytes(pickle.dumps({"chunks": self.chunks, "vectors": self.vectors, "chunk_ids": self._chunk_ids}))
        (path / "config.json").write_text(
            json.dumps({"backend": "faiss", "dimensions": self.dimensions, "normalize": self.normalize}, indent=2),
            encoding="utf-8",
        )

    def load(self, path: Path) -> None:
        index_path = path / "index.faiss"
        metadata_path = path / "metadata.pkl"
        if not index_path.exists() or not metadata_path.exists():
            return
        self._index = self._faiss.read_index(str(index_path))
        payload = pickle.loads(metadata_path.read_bytes())
        self.chunks = dict(payload.get("chunks", {}))
        self.vectors = dict(payload.get("vectors", {}))
        self._chunk_ids = list(payload.get("chunk_ids", self.chunks.keys()))

    def _rebuild_index(self) -> None:
        import numpy as np

        self._index = self._faiss.IndexFlatIP(int(self.dimensions))
        self._chunk_ids = list(self.vectors.keys())
        if not self._chunk_ids:
            return
        matrix = np.array([self.vectors[chunk_id] for chunk_id in self._chunk_ids], dtype="float32")
        self._index.add(matrix)
