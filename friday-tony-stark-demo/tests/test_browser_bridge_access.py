from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from friday.src.common.local_access import LocalAccessMiddleware


EXTENSION_ORIGIN = "chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


class BrowserBridgeAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.add_middleware(LocalAccessMiddleware, enabled=True)

        @app.get("/api/v1/browser-bridge/messenger/command")
        def bridge_route() -> dict[str, bool]:
            return {"ok": True}

        @app.get("/api/v1/health")
        def health_route() -> dict[str, bool]:
            return {"ok": True}

        @app.get("/docs")
        def docs_route() -> dict[str, bool]:
            return {"ok": True}

        self.client = TestClient(app)

    def test_extension_can_only_access_bridge_namespace(self) -> None:
        headers = {"Origin": EXTENSION_ORIGIN, "Sec-Fetch-Site": "cross-site"}
        bridge_response = self.client.get(
            "/api/v1/browser-bridge/messenger/command",
            headers=headers,
        )
        health_response = self.client.get("/api/v1/health", headers=headers)
        self.assertEqual(bridge_response.status_code, 200)
        self.assertEqual(health_response.status_code, 403)

    def test_invalid_extension_origin_is_rejected(self) -> None:
        response = self.client.get(
            "/api/v1/browser-bridge/messenger/command",
            headers={
                "Origin": "chrome-extension://not-a-valid-extension",
                "Sec-Fetch-Site": "cross-site",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_api_docs_allow_only_the_required_swagger_cdn(self) -> None:
        response = self.client.get("/docs")
        policy = response.headers["content-security-policy"]

        self.assertIn("https://cdn.jsdelivr.net", policy)
        self.assertIn("'unsafe-inline'", policy)
        self.assertNotIn("script-src *", policy)

    def test_non_docs_routes_keep_the_strict_self_only_policy(self) -> None:
        response = self.client.get("/api/v1/health")
        policy = response.headers["content-security-policy"]

        self.assertIn("script-src 'self'", policy)
        self.assertNotIn("cdn.jsdelivr.net", policy)


if __name__ == "__main__":
    unittest.main()
