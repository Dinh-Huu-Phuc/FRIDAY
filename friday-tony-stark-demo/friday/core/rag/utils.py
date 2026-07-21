from __future__ import annotations

from pathlib import Path


def infer_source_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".log"}:
        return "logs"
    if "mem" in path.name.lower():
        return "memories"
    if suffix in {".md", ".txt", ".rst"}:
        return "docs"
    return "notes"


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")
