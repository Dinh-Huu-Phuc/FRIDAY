from __future__ import annotations

import re

from friday.app.browser_automation.schemas import (
    BinanceMarketCommand,
    BrowserSearchCommand,
    PlatformVideoSearchCommand,
)
from friday.app.secure_browser.intents import match_secure_browser_intent
from friday.app.secure_browser.schemas import SecureBrowserAction

_BINANCE_ASSETS = {
    "bitcoin": ("BTC", "Bitcoin"),
    "btc": ("BTC", "Bitcoin"),
    "bnb": ("BNB", "BNB"),
    "binance coin": ("BNB", "BNB"),
    "ethereum": ("ETH", "Ethereum"),
    "ether": ("ETH", "Ethereum"),
    "eth": ("ETH", "Ethereum"),
    "solana": ("SOL", "Solana"),
    "sol": ("SOL", "Solana"),
    "xrp": ("XRP", "XRP"),
    "cardano": ("ADA", "Cardano"),
    "ada": ("ADA", "Cardano"),
    "dogecoin": ("DOGE", "Dogecoin"),
    "doge": ("DOGE", "Dogecoin"),
}


_BROWSER_SEARCH_PATTERN = re.compile(
    r"^(?:friday[\s,.:;-]*)?"
    r"(?:please\s+)?(?:open\s+)?(?:a\s+)?"
    r"new\s+(?:chrome\s+)?tab(?:\s+(?:in\s+)?chrome|\s+chrome)?"
    r"\s*(?:and\s+)?(?:search|look\s+up|find)(?:\s+(?:for|about))?\s+"
    r"(?P<query>.+?)\s*$",
    re.IGNORECASE,
)

_NATURAL_BROWSER_SEARCH_PATTERN = re.compile(
    r"^(?:friday[\s,.:;-]*)?"
    r"(?:please\s+)?(?:show\s+me|find\s+and\s+show\s+me|take\s+me\s+to)\s+"
    r"(?:the\s+)?"
    r"(?P<query>.+?)\s*$",
    re.IGNORECASE,
)

_SCREEN_CONTEXT_PATTERN = re.compile(
    r"\b(?:my|this|current)\s+(?:screen|desktop|window)\b|"
    r"\bwhat\s+(?:i(?:'m|\s+am)\s+)?(?:am\s+)?looking\s+at\b",
    re.IGNORECASE,
)

_TRAILING_ACTION_PATTERN = re.compile(
    r"\s+(?:and\s+)?(?:open|read|summarize)\s+"
    r"(?:the\s+)?(?:first\s+)?(?:safe\s+)?result(?:\s+(?:for|to)\s+me)?\s*$",
    re.IGNORECASE,
)

_PLATFORM_VIDEO_SEARCH_PATTERN = re.compile(
    r"^(?:friday[\s,.:;-]*)?"
    r"(?:please\s+)?(?:open|launch|visit|go\s+to)\s+"
    r"(?P<platform>youtube|tik\s*tok)"
    r"\s*(?:and\s+)?(?:search|find|look\s+up)(?:\s+for)?\s+"
    r"(?P<query>.+?)\s*$",
    re.IGNORECASE,
)


def parse_browser_search_command(message: str) -> BrowserSearchCommand | None:
    candidate = str(message or "").strip()
    match = _BROWSER_SEARCH_PATTERN.fullmatch(candidate)
    if not match:
        match = _NATURAL_BROWSER_SEARCH_PATTERN.fullmatch(candidate)
    if not match:
        browser_intent = match_secure_browser_intent(candidate)
        if (
            browser_intent.action == SecureBrowserAction.OPEN
            and browser_intent.query
        ):
            return BrowserSearchCommand(query=browser_intent.query)
        return None

    query = _TRAILING_ACTION_PATTERN.sub("", match.group("query"))
    query = query.strip(" \t\r\n.,!?;:\"'")
    if not query or len(query) > 300 or _SCREEN_CONTEXT_PATTERN.search(query):
        return None
    return BrowserSearchCommand(query=query)


def is_browser_search_request(message: str) -> bool:
    return parse_browser_search_command(message) is not None


def parse_binance_market_command(message: str) -> BinanceMarketCommand | None:
    original = " ".join(str(message or "").split())
    candidate = original.lower()
    if "binance" not in candidate:
        return None
    for alias in sorted(_BINANCE_ASSETS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", candidate):
            symbol, asset_name = _BINANCE_ASSETS[alias]
            return BinanceMarketCommand(symbol=symbol, asset_name=asset_name)
    ignored = {"FRIDAY", "BINANCE", "USDT", "USD"}
    for token in re.findall(r"\b[A-Z][A-Z0-9]{1,11}\b", original):
        if token not in ignored:
            return BinanceMarketCommand(symbol=token, asset_name=token)
    return None


def is_binance_market_request(message: str) -> bool:
    return parse_binance_market_command(message) is not None


def parse_platform_video_search_command(
    message: str,
) -> PlatformVideoSearchCommand | None:
    candidate = str(message or "").strip()
    match = _PLATFORM_VIDEO_SEARCH_PATTERN.fullmatch(candidate)
    if not match:
        return None

    platform = re.sub(r"\s+", "", match.group("platform").lower())
    query = match.group("query").strip(" \t\r\n.,!?;:\"'")
    if not query or len(query) > 200:
        return None
    return PlatformVideoSearchCommand(platform=platform, query=query)


def is_platform_video_search_request(message: str) -> bool:
    return parse_platform_video_search_command(message) is not None
