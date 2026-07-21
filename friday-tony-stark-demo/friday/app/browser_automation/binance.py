from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import dotenv_values


APP_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
DEFAULT_OVERVIEW_URL = "https://www.binance.com/vi/markets/overview"
DEFAULT_TRADE_URL = "https://www.binance.com/vi/trade/BTC_USDT?_from=markets"


def get_binance_urls(symbol: str) -> tuple[str, str]:
    normalized_symbol = str(symbol or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{2,12}", normalized_symbol):
        raise ValueError("The Binance asset symbol is invalid.")

    values = dotenv_values(APP_ENV_PATH)
    overview = _safe_binance_url(
        values.get("BINANCE_URL_VI_MARKET_OVERVIEW")
        or os.getenv("BINANCE_URL_VI_MARKET_OVERVIEW"),
        DEFAULT_OVERVIEW_URL,
    )
    trade_template = _safe_binance_url(
        values.get("BINANCE_URL") or os.getenv("BINANCE_URL"),
        DEFAULT_TRADE_URL,
    )
    trade = _replace_trade_pair(trade_template, f"{normalized_symbol}_USDT")
    return overview, trade


def _safe_binance_url(value: object, fallback: str) -> str:
    candidate = str(value or "").strip()
    parsed = urlsplit(candidate)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (
        hostname == "binance.com" or hostname.endswith(".binance.com")
    ):
        return fallback
    return candidate


def _replace_trade_pair(url: str, pair: str) -> str:
    parsed = urlsplit(url)
    path = re.sub(r"(?i)(/trade/)[^/?#]+", rf"\g<1>{pair}", parsed.path, count=1)
    if path == parsed.path and "/trade/" not in parsed.path.lower():
        path = f"/vi/trade/{pair}"
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))
