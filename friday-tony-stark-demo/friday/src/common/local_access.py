from __future__ import annotations

import ipaddress
import re
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit


ASGIApp = Callable[[dict, Callable, Callable], Awaitable[None]]
_CHROME_EXTENSION_ID = re.compile(r"[a-p]{32}")
_DEFAULT_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; media-src 'self' blob:; connect-src 'self' "
    "ws://127.0.0.1:* ws://localhost:*; object-src 'none'; "
    "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
)
_API_DOCS_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; "
    "frame-ancestors 'none'; form-action 'self'"
)


def _is_loopback_host(value: str) -> bool:
    normalized = value.strip().rstrip(".").lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _hostname(value: str) -> str:
    try:
        return urlsplit(value if "://" in value else f"//{value}").hostname or ""
    except ValueError:
        return ""


def _is_chrome_extension_origin(value: str) -> bool:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return (
        parsed.scheme.lower() == "chrome-extension"
        and bool(_CHROME_EXTENSION_ID.fullmatch(parsed.hostname or ""))
    )


def _content_security_policy(path: str) -> str:
    if path == "/docs" or path.startswith("/docs/") or path == "/redoc":
        return _API_DOCS_CONTENT_SECURITY_POLICY
    return _DEFAULT_CONTENT_SECURITY_POLICY


class LocalAccessMiddleware:
    """Keep the personal core local and reject browser requests from foreign origins."""

    def __init__(self, app: ASGIApp, *, enabled: bool = True) -> None:
        self.app = app
        self.enabled = enabled

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        client_host = str((scope.get("client") or ("", 0))[0])
        test_client = client_host == "testclient"
        request_host = _hostname(headers.get("host", ""))
        host_allowed = _is_loopback_host(request_host) or (test_client and request_host == "testserver")
        client_allowed = _is_loopback_host(client_host) or test_client

        origin = headers.get("origin", "")
        path = str(scope.get("path") or "")
        extension_bridge_request = (
            path.startswith("/api/v1/browser-bridge/")
            and _is_chrome_extension_origin(origin)
        )
        origin_allowed = not origin or _is_loopback_host(_hostname(origin)) or extension_bridge_request
        fetch_site_allowed = (
            headers.get("sec-fetch-site", "") != "cross-site" or extension_bridge_request
        )

        if self.enabled and not (host_allowed and client_allowed and origin_allowed and fetch_site_allowed):
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008, "reason": "Local access only"})
            else:
                body = b'{"detail":"Local access only"}'
                await send(
                    {
                        "type": "http.response.start",
                        "status": 403,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode("ascii")),
                            (b"cache-control", b"no-store"),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": body})
            return

        async def send_hardened(message: dict) -> None:
            if message["type"] == "http.response.start":
                response_headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() not in {b"server", b"x-powered-by"}
                ]
                response_headers.extend(
                    [
                        (
                            b"content-security-policy",
                            _content_security_policy(path).encode("ascii"),
                        ),
                        (b"referrer-policy", b"no-referrer"),
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"cross-origin-opener-policy", b"same-origin"),
                        (b"permissions-policy", b"camera=(), geolocation=(), microphone=(self)"),
                    ]
                )
                if not any(key.lower() == b"cache-control" for key, _ in response_headers):
                    response_headers.append((b"cache-control", b"no-store"))
                message["headers"] = response_headers
            await send(message)

        await self.app(scope, receive, send_hardened)
