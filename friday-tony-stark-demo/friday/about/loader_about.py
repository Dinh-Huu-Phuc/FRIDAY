from __future__ import annotations

import re
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


def _normalized_key(value: str) -> str:
    return "_".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _trigger_topic(section_name: str) -> str | None:
    match = re.match(r"^(.*?)\s*Triggers?$", section_name, flags=re.IGNORECASE)
    if not match:
        return None
    return _normalized_key(match.group(1)) or "introduction"


def _response_descriptor(section_name: str) -> tuple[str, str, str] | None:
    legacy_key = _response_key(section_name)
    if legacy_key is not None:
        return "introduction", "en", legacy_key
    if not section_name.casefold().endswith(" response"):
        return None

    words = section_name[: -len(" response")].split()
    language = "en"
    mode = "full"
    if words and words[0].casefold() == "vietnamese":
        language = "vi"
        words.pop(0)
    if words and words[0].casefold() in {"full", "short", "voice"}:
        mode = words.pop(0).casefold()
    topic = _normalized_key(" ".join(words)) or "introduction"
    return topic, language, mode


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
    trigger_groups: dict[str, tuple[str, ...]] = {}

    for section_name, section_body in sections.items():
        trigger_topic = _trigger_topic(section_name)
        if trigger_topic is not None:
            trigger_groups[trigger_topic] = _parse_trigger_lines(section_body)

        descriptor = _response_descriptor(section_name)
        if descriptor is None or not section_body:
            continue
        topic, language, mode = descriptor
        responses[f"{topic}_{language}_{mode}"] = section_body
        if topic == "introduction":
            responses[f"{language}_{mode}"] = section_body
            if language == "en":
                responses[mode] = section_body

    introduction_triggers = trigger_groups.get("introduction", ())

    return AboutDocument(
        id=_slug_from_filename(path),
        path=path,
        title=title,
        triggers=introduction_triggers,
        trigger_groups=trigger_groups,
        responses=responses,
        sections={_normalized_key(key): value for key, value in sections.items()},
        important_rule=_section(
            sections,
            "Important Rule",
            "Safety Rule",
            "Safety and Accuracy Rules",
        ),
    )


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
