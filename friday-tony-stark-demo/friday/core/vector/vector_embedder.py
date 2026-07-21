from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .vector_similarity import normalize_vector


class EmbeddingModel(Protocol):
    dimensions: int

    def embed_text(self, text: str) -> list[float]:
        ...


@dataclass(slots=True)
class HashEmbeddingModel:
    dimensions: int = 128
    normalize: bool = True

    def embed_text(self, text: str) -> list[float]:
        dims = max(8, self.dimensions)
        vec = [0.0] * dims
        tokens = [token for token in text.lower().split() if token]
        if not tokens:
            return vec
        for idx, token in enumerate(tokens):
            bucket = (hash(token) + idx) % dims
            val = (sum(ord(c) for c in token) % 211) / 211.0
            vec[bucket] += val
        length = max(1, len(tokens))
        vector = [v / length for v in vec]
        return normalize_vector(vector) if self.normalize else vector


@dataclass(slots=True)
class SentenceTransformerEmbeddingModel:
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    normalize: bool = True
    dimensions: int = field(init=False)
    _model: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - depends on optional package
            raise RuntimeError(
                "sentence-transformers is required for SentenceTransformerEmbeddingModel. "
                "Install sentence-transformers or use HashEmbeddingModel."
            ) from exc
        self._model = SentenceTransformer(self.model_name)
        self.dimensions = int(self._model.get_sentence_embedding_dimension())

    def embed_text(self, text: str) -> list[float]:
        vector = self._model.encode(text or "", normalize_embeddings=self.normalize)
        return [float(value) for value in vector.tolist()]
