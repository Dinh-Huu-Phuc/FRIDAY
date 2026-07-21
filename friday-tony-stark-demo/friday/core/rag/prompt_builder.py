from __future__ import annotations

from ..schemas.rag_entities import RetrievedChunk
from .citations import build_citations


def build_rag_prompt_context(chunks: list[RetrievedChunk], *, max_chars: int = 2400) -> str:
    if not chunks:
        return ""
    lines = []
    total = 0
    for idx, item in enumerate(chunks, start=1):
        snippet = item.chunk.text.strip().replace("\n", " ")
        block = f"[{idx}] {snippet}\n"
        if total + len(block) > max_chars:
            break
        total += len(block)
        lines.append(block)
    cites = "\n".join(build_citations(chunks[: len(lines)]))
    return f"Retrieved context:\n{''.join(lines)}\nCitations:\n{cites}".strip()
