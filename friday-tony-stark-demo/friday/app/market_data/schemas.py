from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CryptoPriceRequest:
    symbol: str
    asset_name: str
    quote_symbol: str = "USDT"

    @property
    def pair(self) -> str:
        return f"{self.symbol}{self.quote_symbol}"


@dataclass(frozen=True, slots=True)
class CryptoPriceResult:
    ok: bool
    request: CryptoPriceRequest
    message: str
    source_url: str = ""
    excerpt: str = ""
