"""Intent parsing for live cryptocurrency price questions."""

from __future__ import annotations

import re

from .schemas import CryptoPriceRequest


_ASSETS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("BTC", "Bitcoin", ("bitcoin", "btc")),
    ("ETH", "Ethereum", ("ethereum", "ether", "eth")),
    ("BNB", "BNB", ("binance coin", "bnb")),
    ("SOL", "Solana", ("solana", "sol")),
    ("XRP", "XRP", ("ripple", "xrp")),
    ("ADA", "Cardano", ("cardano", "ada")),
    ("DOGE", "Dogecoin", ("dogecoin", "doge")),
    ("AVAX", "Avalanche", ("avalanche", "avax")),
    ("DOT", "Polkadot", ("polkadot", "dot")),
    ("TRX", "TRON", ("tron", "trx")),
    ("LINK", "Chainlink", ("chainlink", "link")),
    ("LTC", "Litecoin", ("litecoin", "ltc")),
    ("TON", "Toncoin", ("toncoin", "ton")),
    ("SHIB", "Shiba Inu", ("shiba inu", "shib")),
    ("SUI", "Sui", ("sui",)),
)
_PRICE_SIGNAL = re.compile(
    r"\b(?:price|worth|value|trading at|exchange rate)\b|\bhow much (?:is|does)\b",
    re.IGNORECASE,
)


def parse_crypto_price_request(message: str) -> CryptoPriceRequest | None:
    normalized = " ".join(str(message or "").lower().replace("’", "'").split())
    if not normalized or not _PRICE_SIGNAL.search(normalized):
        return None

    for symbol, asset_name, aliases in _ASSETS:
        for alias in sorted(aliases, key=len, reverse=True):
            if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", normalized):
                return CryptoPriceRequest(symbol=symbol, asset_name=asset_name)
    return None
