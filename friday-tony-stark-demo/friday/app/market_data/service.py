"""Public market-data access for answers that must not rely on model memory."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from urllib.parse import urlencode

import httpx

from .schemas import CryptoPriceRequest, CryptoPriceResult


DEFAULT_MARKET_DATA_BASE_URL = "https://data-api.binance.vision"


def get_crypto_price(
    request: CryptoPriceRequest,
    *,
    client: httpx.Client | None = None,
    base_url: str | None = None,
) -> CryptoPriceResult:
    active_base_url = (
        base_url
        or os.getenv("FRIDAY_MARKET_DATA_BASE_URL")
        or DEFAULT_MARKET_DATA_BASE_URL
    ).rstrip("/")
    endpoint = f"{active_base_url}/api/v3/ticker/price"
    source_url = f"{endpoint}?{urlencode({'symbol': request.pair})}"
    owns_client = client is None
    active_client = client or httpx.Client(
        timeout=_request_timeout(),
        follow_redirects=True,
    )
    try:
        response = active_client.get(endpoint, params={"symbol": request.pair})
        response.raise_for_status()
        raw_price = str(response.json().get("price", "")).strip()
        price = Decimal(raw_price)
        if not price.is_finite() or price <= 0:
            raise ValueError("Market data returned an invalid price")
    except (httpx.HTTPError, InvalidOperation, TypeError, ValueError, AttributeError):
        return CryptoPriceResult(
            ok=False,
            request=request,
            message=(
                f"The live {request.asset_name} price service is temporarily unavailable."
            ),
            source_url=source_url,
        )
    finally:
        if owns_client:
            active_client.close()

    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    displayed_price = _format_price(price)
    excerpt = (
        f"Binance Spot public market data reports {request.asset_name} "
        f"({request.symbol}) at {displayed_price} {request.quote_symbol} per "
        f"{request.symbol} for pair {request.pair}, checked at {checked_at}. "
        "This live quote can change continuously."
    )
    return CryptoPriceResult(
        ok=True,
        request=request,
        message=(
            f"{request.asset_name} is currently trading at approximately "
            f"{displayed_price} {request.quote_symbol} on Binance Spot "
            f"(checked at {checked_at}). The quote can change continuously. "
            f"Source: {source_url}"
        ),
        source_url=source_url,
        excerpt=excerpt,
    )


def _format_price(price: Decimal) -> str:
    if price >= Decimal("1000"):
        precision = Decimal("0.01")
    elif price >= Decimal("1"):
        precision = Decimal("0.0001")
    else:
        precision = Decimal("0.00000001")
    return f"{price.quantize(precision, rounding=ROUND_HALF_UP):,f}"


def _request_timeout() -> float:
    try:
        return max(1.0, min(15.0, float(os.getenv("FRIDAY_MARKET_DATA_TIMEOUT", "5"))))
    except ValueError:
        return 5.0
