from __future__ import annotations

import unittest
from unittest.mock import patch

from friday.app.market_data import (
    CryptoPriceRequest,
    CryptoPriceResult,
    get_crypto_price,
    parse_crypto_price_request,
)
from friday.app.research import LiveSearchResult, research_public_web


class _FakeResponse:
    def __init__(self, price: str) -> None:
        self._price = price

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"symbol": "BTCUSDT", "price": self._price}


class _FakeClient:
    def __init__(self, price: str = "67234.12500000") -> None:
        self.price = price
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, url: str, *, params: dict[str, str]):
        self.calls.append((url, params))
        return _FakeResponse(self.price)


class MarketDataTests(unittest.TestCase):
    def test_parser_understands_flexible_crypto_price_questions(self) -> None:
        samples = (
            ("Please tell me today's Bitcoin price.", "BTC"),
            ("How much is Ethereum worth right now?", "ETH"),
            ("What is the current SOL value?", "SOL"),
            ("Friday, give me the BNB price", "BNB"),
        )
        for message, expected_symbol in samples:
            with self.subTest(message=message):
                request = parse_crypto_price_request(message)
                self.assertIsNotNone(request)
                self.assertEqual(request.symbol, expected_symbol)

    def test_parser_does_not_hijack_non_price_crypto_requests(self) -> None:
        self.assertIsNone(parse_crypto_price_request("Explain Bitcoin mining"))
        self.assertIsNone(parse_crypto_price_request("Open Binance Bitcoin market"))

    def test_market_service_uses_public_spot_ticker_endpoint(self) -> None:
        client = _FakeClient()
        request = CryptoPriceRequest(symbol="BTC", asset_name="Bitcoin")

        result = get_crypto_price(
            request,
            client=client,
            base_url="https://data-api.binance.vision",
        )

        self.assertTrue(result.ok)
        self.assertIn("67,234.13 USDT", result.message)
        self.assertIn("BTCUSDT", result.excerpt)
        self.assertEqual(
            client.calls,
            [
                (
                    "https://data-api.binance.vision/api/v3/ticker/price",
                    {"symbol": "BTCUSDT"},
                )
            ],
        )

    def test_research_prefers_market_data_and_falls_back_to_web(self) -> None:
        request = CryptoPriceRequest(symbol="BTC", asset_name="Bitcoin")
        market_result = CryptoPriceResult(
            ok=True,
            request=request,
            message="Bitcoin is currently 67,234.13 USDT.",
            source_url="https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT",
            excerpt="Binance Spot reports BTCUSDT at 67,234.13 USDT.",
        )
        with (
            patch(
                "friday.app.research.service.get_crypto_price",
                return_value=market_result,
            ),
            patch("friday.app.research.service.search_public_web") as web_search,
        ):
            result = research_public_web("Please tell me today's Bitcoin price.")

        self.assertTrue(result.ok)
        self.assertEqual(result.direct_answer, market_result.message)
        self.assertEqual(result.sources[0].title, "Binance Spot BTCUSDT live price")
        web_search.assert_not_called()

        unavailable = CryptoPriceResult(
            ok=False,
            request=request,
            message="Market data unavailable.",
        )
        fallback = LiveSearchResult(
            ok=False,
            query="today's Bitcoin price",
            message="Search unavailable.",
        )
        with (
            patch(
                "friday.app.research.service.get_crypto_price",
                return_value=unavailable,
            ),
            patch(
                "friday.app.research.service.search_public_web",
                return_value=fallback,
            ) as web_search,
        ):
            result = research_public_web("Please tell me today's Bitcoin price.")

        self.assertIs(result, fallback)
        web_search.assert_called_once_with("today's Bitcoin price")


if __name__ == "__main__":
    unittest.main()
