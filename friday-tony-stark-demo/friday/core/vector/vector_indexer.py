from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .vector_embedder import EmbeddingModel
from .vector_schemas import VectorRecord
from .vector_store import VectorStore


@dataclass(slots=True)
class VectorIndexer:
    embedding_model: EmbeddingModel
    store: VectorStore

    def index_chunks(self, chunks: list[VectorRecord]) -> int:
        for chunk in chunks:
            vector = self.embedding_model.embed_text(chunk.text)
            self.store.upsert(chunk, vector)
        return len(chunks)

    def delete_chunk(self, chunk_id: str) -> None:
        self.store.delete(chunk_id)

    def write_chunks_jsonl(self, chunks: list[VectorRecord], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file_obj:
            for chunk in chunks:
                file_obj.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")

    def write_embeddings_jsonl(self, chunks: list[VectorRecord], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file_obj:
            for chunk in chunks:
                vector = self.embedding_model.embed_text(chunk.text)
                file_obj.write(
                    json.dumps(
                        {
                            "id": chunk.id,
                            "chunk_id": chunk.chunk_id,
                            "vector": vector,
                            "metadata": {
                                "source_path": chunk.source_path,
                                "source_type": chunk.source_type,
                                "title": chunk.title,
                                "tags": chunk.tags,
                                "created_at": chunk.created_at,
                            },
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

    def save_index(self, path: Path) -> None:
        self.store.dump(path)

    def load_index(self, path: Path) -> None:
        self.store.load(path)
