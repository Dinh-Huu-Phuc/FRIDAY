from __future__ import annotations

from friday.core.vector.vector_schemas import VectorSearchResult


def build_citations(chunks: list[VectorSearchResult]) -> list[str]:
    citations = []
    for idx, item in enumerate(chunks, start=1):
        title = item.chunk.title or item.chunk.source_path
        citations.append(f"[{idx}] {title} ({item.chunk.source_type}) - {item.chunk.source_path}")
    return citations
