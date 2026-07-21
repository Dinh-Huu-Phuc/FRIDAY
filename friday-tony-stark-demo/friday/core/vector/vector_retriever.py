from __future__ import annotations

from dataclasses import dataclass

from ..constants import DEFAULT_TOP_K
from .vector_embedder import EmbeddingModel
from .vector_schemas import VectorSearchResult
from .vector_store import VectorStore


@dataclass(slots=True)
class VectorRetriever:
    embedding_model: EmbeddingModel
    store: VectorStore

    def retrieve(self, query: str, *, top_k: int = DEFAULT_TOP_K) -> list[VectorSearchResult]:
        query_vector = self.embedding_model.embed_text(query)
        return self.store.query(query_vector, top_k=top_k)
