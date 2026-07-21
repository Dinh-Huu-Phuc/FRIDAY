from __future__ import annotations

from ..schemas.rag_entities import RetrievedChunk


def build_citations(chunks: list[RetrievedChunk]) -> list[str]:
    citations = []
    for idx, item in enumerate(chunks, start=1):
        title = item.chunk.title or item.chunk.source_path
        citations.append(f"[{idx}] {title} ({item.chunk.source_type})")
    return citations
