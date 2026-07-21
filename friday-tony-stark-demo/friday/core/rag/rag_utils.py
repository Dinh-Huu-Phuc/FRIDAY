from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def infer_source_type(path: Path) -> str:
    parts = {part.lower() for part in path.parts}
    for category in ("docs", "memories", "logs", "notes"):
        if category in parts:
            return category
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


def parse_markdown_knowledge(text: str, *, fallback_title: str) -> tuple[str, dict[str, Any]]:
    lines = text.splitlines()
    metadata: dict[str, Any] = {}
    content_start = 0
    title = fallback_title

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip() or fallback_title
            content_start = index + 1
            break

    cursor = content_start
    while cursor < len(lines):
        stripped = lines[cursor].strip()
        if not stripped:
            cursor += 1
            continue
        if stripped.lower() == "## content":
            cursor += 1
            break
        match = re.match(r"^[-*]\s*([A-Za-z0-9_-]+)\s*:\s*(.+)$", stripped)
        if not match:
            break
        metadata[match.group(1).lower()] = match.group(2).strip()
        cursor += 1

    metadata.setdefault("title", title)
    content = "\n".join(lines[cursor:]).strip() or text.strip()
    return content, metadata
