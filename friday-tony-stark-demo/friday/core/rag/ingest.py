from __future__ import annotations

from pathlib import Path

from ..schemas.rag_entities import Document
from .utils import infer_source_type, safe_read_text


def ingest_documents_from_paths(paths: list[Path]) -> list[Document]:
    documents: list[Document] = []
    for path in paths:
        if path.is_dir():
            documents.extend(ingest_documents_from_paths(list(path.rglob("*"))))
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".txt", ".log", ".json"}:
            continue
        text = safe_read_text(path).strip()
        if not text:
            continue
        documents.append(
            Document(
                text=text,
                source_path=str(path),
                source_type=infer_source_type(path),
                title=path.stem,
            )
        )
    return documents
