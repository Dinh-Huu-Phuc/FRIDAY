from __future__ import annotations

from pathlib import Path

from friday.core.vector.vector_schemas import VectorDocument
from friday.core.vector.vector_utils import parse_tags, stable_id

from .rag_utils import infer_source_type, parse_markdown_knowledge, safe_read_text


def ingest_documents_from_paths(paths: list[Path]) -> list[VectorDocument]:
    documents: list[VectorDocument] = []
    for path in paths:
        if path.is_dir():
            documents.extend(ingest_documents_from_paths(list(path.rglob("*"))))
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".txt", ".log"}:
            continue
        raw_text = safe_read_text(path).strip()
        if path.suffix.lower() == ".md":
            text, metadata = parse_markdown_knowledge(raw_text, fallback_title=path.stem)
        else:
            text = raw_text
            metadata = {"title": path.stem}
        if not text:
            continue
        source_type = infer_source_type(path)
        metadata["category"] = source_type
        metadata.setdefault("source", str(path))
        documents.append(
            VectorDocument(
                id=stable_id(str(path.resolve())),
                text=text,
                source_path=str(path),
                source_type=source_type,
                title=str(metadata.get("title") or path.stem),
                tags=parse_tags(metadata.get("tags")),
                created_at=str(metadata.get("date") or metadata.get("created_at") or "") or None,
                metadata=metadata,
            )
        )
    return documents
