from __future__ import annotations

from dataclasses import dataclass

from ..constants import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE
from ..schemas.rag_entities import Chunk, Document


@dataclass(slots=True)
class TextChunker:
    chunk_size: int = DEFAULT_CHUNK_SIZE
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP

    def chunk(self, document: Document) -> list[Chunk]:
        text = document.text.strip()
        if not text:
            return []
        chunks: list[Chunk] = []
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
                    Chunk(
                        chunk_id=f"{document.source_path}::{index}",
                        text=piece,
                        source_path=document.source_path,
                        source_type=document.source_type,
                        title=document.title,
                        metadata=dict(document.metadata),
                    )
                )
                index += 1
            if end >= len(text):
                break
            start += step
        return chunks
