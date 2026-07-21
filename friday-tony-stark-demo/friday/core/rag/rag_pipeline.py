from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from friday.core.vector import EmbeddingModel, VectorIndexer, VectorRecord, VectorStore

from .rag_chunker import RagChunker
from .rag_ingest import ingest_documents_from_paths


@dataclass(slots=True)
class RagIngestPipeline:
    chunker: RagChunker
    indexer: VectorIndexer

    @classmethod
    def create(cls, *, embedding_model: EmbeddingModel, store: VectorStore, chunk_size: int, chunk_overlap: int) -> "RagIngestPipeline":
        return cls(
            chunker=RagChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap),
            indexer=VectorIndexer(embedding_model=embedding_model, store=store),
        )

    def build_chunks(self, paths: list[Path]) -> list[VectorRecord]:
        chunks: list[VectorRecord] = []
        for document in ingest_documents_from_paths(paths):
            chunks.extend(self.chunker.chunk(document))
        return chunks

    def index_paths(self, paths: list[Path]) -> int:
        return self.indexer.index_chunks(self.build_chunks(paths))
