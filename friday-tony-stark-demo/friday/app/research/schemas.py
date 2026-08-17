from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class LiveSearchSource:
    title: str
    url: str
    excerpt: str


@dataclass(frozen=True, slots=True)
class LiveSearchResult:
    ok: bool
    query: str
    message: str
    sources: tuple[LiveSearchSource, ...] = field(default_factory=tuple)
    candidate_count: int = 0
    direct_answer: str = ""

    @property
    def url(self) -> str:
        return self.sources[0].url if self.sources else ""

    @property
    def title(self) -> str:
        return self.sources[0].title if self.sources else ""

    @property
    def excerpt(self) -> str:
        return self.sources[0].excerpt if self.sources else ""
