from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AboutDocument:
    id: str
    path: Path
    title: str
    triggers: tuple[str, ...] = field(default_factory=tuple)
    trigger_groups: dict[str, tuple[str, ...]] = field(default_factory=dict)
    responses: dict[str, str] = field(default_factory=dict)
    sections: dict[str, str] = field(default_factory=dict)
    important_rule: str = ""


@dataclass(frozen=True, slots=True)
class AboutMatch:
    matched: bool
    document_id: str = ""
    response_type: str = "voice"
    response: str = ""
    trigger: str = ""
