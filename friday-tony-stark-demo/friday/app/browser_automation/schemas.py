from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BrowserSearchCommand:
    query: str


@dataclass(frozen=True, slots=True)
class PlatformVideoSearchCommand:
    platform: str
    query: str


@dataclass(frozen=True, slots=True)
class BinanceMarketCommand:
    symbol: str
    asset_name: str


@dataclass(frozen=True, slots=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str = ""


@dataclass(frozen=True, slots=True)
class BrowserAutomationResult:
    ok: bool
    query: str
    message: str
    title: str = ""
    url: str = ""
    excerpt: str = ""


@dataclass(frozen=True, slots=True)
class PlatformVideoSearchResult:
    ok: bool
    platform: str
    query: str
    selected_rank: int
    message: str
