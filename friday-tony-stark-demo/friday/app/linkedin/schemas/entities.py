"""Domain entities for the LinkedIn package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class LinkedInProfileEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "profile"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class LinkedInPostEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "post"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class LinkedInCompanyPageEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "company_page"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class LinkedInCommentEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "comment"
    metadata: dict[str, Any] = field(default_factory=dict)
