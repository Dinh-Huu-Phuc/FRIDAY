from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..schemas.rag_entities import Chunk
from .embeddings import EmbeddingModel
from .store import VectorStore


@dataclass(slots=True)
class RagIndexer:
    embedding_model: EmbeddingModel
    store: VectorStore

    def index_chunks(self, chunks: list[Chunk]) -> int:
        for chunk in chunks:
            vector = self.embedding_model.embed_text(chunk.text)
            self.store.upsert(chunk, vector)
        return len(chunks)

    def save_index(self, path: Path) -> None:
        self.store.dump(path)

    def load_index(self, path: Path) -> None:
        self.store.load(path)
