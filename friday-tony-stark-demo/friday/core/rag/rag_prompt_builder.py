from __future__ import annotations

from friday.core.vector.vector_schemas import VectorSearchResult

from .rag_citations import build_citations


def build_rag_prompt_context(chunks: list[VectorSearchResult], *, max_chars: int = 2400) -> str:
    if not chunks:
        return ""
    lines = []
    total = 0
    for idx, item in enumerate(chunks, start=1):
        snippet = item.chunk.text.strip().replace("\n", " ")
        title = item.chunk.title or item.chunk.source_path
        tags = ", ".join(item.chunk.tags)
        source = f"{title} | {item.chunk.source_type}"
        if tags:
            source = f"{source} | tags: {tags}"
        block = f"[{idx}] source: {source}\n{snippet}\n"
        if total + len(block) > max_chars:
            break
        total += len(block)
        lines.append(block)
    cites = "\n".join(build_citations(chunks[: len(lines)]))
    context = "\n".join(lines)
    return f"Retrieved context:\n{context}\n\nCitations:\n{cites}".strip()
