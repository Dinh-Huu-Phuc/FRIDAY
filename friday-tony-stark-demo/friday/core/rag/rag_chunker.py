from __future__ import annotations

from dataclasses import dataclass

from friday.core.vector.vector_schemas import VectorDocument, VectorRecord
from friday.core.vector.vector_utils import stable_id

from ..constants import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE


@dataclass(slots=True)
class RagChunker:
    chunk_size: int = DEFAULT_CHUNK_SIZE
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP

    def chunk(self, document: VectorDocument) -> list[VectorRecord]:
        text = document.text.strip()
        if not text:
            return []
        chunks: list[VectorRecord] = []
        start = 0
        index = 0
        size = max(64, int(self.chunk_size))
        overlap = max(0, min(int(self.chunk_overlap), size // 2))
        step = max(1, size - overlap)

        while start < len(text):
            end = min(len(text), start + size)
            piece = text[start:end].strip()
            if piece:
                chunks.append(
                    VectorRecord(
                        id=stable_id(f"{document.id}:{index}"),
                        chunk_id=f"{document.source_path}::{index}",
                        text=piece,
                        source_path=document.source_path,
                        source_type=document.source_type,
                        title=document.title,
                        tags=list(document.tags),
                        created_at=document.created_at,
                        metadata=dict(document.metadata),
                    )
                )
                index += 1
            if end >= len(text):
                break
            start += step
        return chunks


TextChunker = RagChunker
