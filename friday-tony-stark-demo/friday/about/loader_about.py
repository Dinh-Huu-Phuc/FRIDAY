from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from friday.about.schemas_about import AboutDocument


ABOUT_DIR = Path(__file__).resolve().parent
ABOUT_MESSAGES_DIR = ABOUT_DIR / "messages"
SELF_INTRO_DOCUMENT_ID = "friday_self_intro"
SELF_INTRO_FILE = "friday_self_intro_response.md"


def _slug_from_filename(path: Path) -> str:
    name = path.stem
    return name.removesuffix("_response")


def _read_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _split_sections(markdown: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = "__preamble__"
    sections[current] = []

    for line in markdown.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            current = match.group(1).strip()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)

    return {key: "\n".join(value).strip() for key, value in sections.items()}


def _parse_trigger_lines(section: str) -> tuple[str, ...]:
    triggers: list[str] = []
    for line in section.splitlines():
        candidate = line.strip()
        if not candidate.startswith("-"):
            continue
        candidate = candidate[1:].strip().strip('"').strip("'")
        if candidate:
            triggers.append(candidate)
    return tuple(triggers)


def _response_key(section_name: str) -> str | None:
    match = re.match(r"Response\s*:\s*(.+)", section_name, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip().lower().replace(" ", "_")
    match = re.match(r"(Full|Short|Voice)\s+Response$", section_name, flags=re.IGNORECASE)
    return match.group(1).lower() if match else None


def _section(sections: dict[str, str], *names: str) -> str:
    expected = {name.casefold() for name in names}
    for section_name, body in sections.items():
        if section_name.casefold() in expected:
            return body
    return ""


def load_about_document(path: Path) -> AboutDocument:
    markdown = _read_markdown(path)
    sections = _split_sections(markdown)
    title = sections.get("__preamble__", "").strip().lstrip("# ").strip() or path.stem
    responses: dict[str, str] = {}

    for section_name, section_body in sections.items():
        key = _response_key(section_name)
        if key and section_body:
            responses[key] = section_body

    return AboutDocument(
        id=_slug_from_filename(path),
        path=path,
        title=title,
        triggers=_parse_trigger_lines(_section(sections, "Trigger", "Triggers")),
        responses=responses,
        important_rule=_section(sections, "Important Rule", "Safety Rule"),
    )


@lru_cache(maxsize=1)
def load_about_documents() -> dict[str, AboutDocument]:
    documents: dict[str, AboutDocument] = {}
    for path in sorted(ABOUT_MESSAGES_DIR.glob("*.md")):
        document = load_about_document(path)
        documents[document.id] = document
    return documents


def load_self_intro_document() -> AboutDocument:
    documents = load_about_documents()
    if SELF_INTRO_DOCUMENT_ID in documents:
        return documents[SELF_INTRO_DOCUMENT_ID]
    return load_about_document(ABOUT_MESSAGES_DIR / SELF_INTRO_FILE)
