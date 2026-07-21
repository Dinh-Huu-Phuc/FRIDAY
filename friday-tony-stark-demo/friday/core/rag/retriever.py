from __future__ import annotations

from dataclasses import dataclass

from ..constants import DEFAULT_TOP_K
from ..schemas.rag_entities import RetrievedChunk
from .embeddings import EmbeddingModel
from .store import VectorStore


@dataclass(slots=True)
class RagRetriever:
    embedding_model: EmbeddingModel
    store: VectorStore

    def retrieve(self, query: str, *, top_k: int = DEFAULT_TOP_K) -> list[RetrievedChunk]:
        query_vector = self.embedding_model.embed_text(query)
        return self.store.query(query_vector, top_k=top_k)
