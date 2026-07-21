from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class EmbeddingModel(Protocol):
    dimensions: int

    def embed_text(self, text: str) -> list[float]:
        ...


@dataclass(slots=True)
class HashEmbeddingModel:
    dimensions: int = 128

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
        return [v / length for v in vec]
