"""Low-level client for Discord operations."""

from __future__ import annotations

from friday.app.common.browser import BrowserManager, TabOpenResult
from friday.app.discord.config.settings import DiscordSettings
from friday.app.discord.schemas.requests import (
    GetPostDetailRequest,
    GetProfileRequest,
    PublishContentRequest,
    SearchContentRequest,
)
from friday.app.discord.utils.helpers import build_resource_url, normalize_identifier


class DiscordClient:
    """Thin client that prepares low-level payloads for Discord."""

    def __init__(
        self,
        *,
        settings: DiscordSettings,
        browser_manager: BrowserManager | None = None,
    ) -> None:
        self.settings = settings
        self.browser_manager = browser_manager or BrowserManager()

    def open_homepage(self) -> TabOpenResult:
        return self.browser_manager.open_url(
            platform_name=self.settings.platform_name,
            url=self.settings.website_url,
        )

    def get_profile(self, request: GetProfileRequest) -> dict[str, object]:
        identifier = normalize_identifier(request.identifier or request.username or self.settings.platform_name)
        return {
            "id": identifier,
            "url": build_resource_url(self.settings.website_url, "guild", identifier),
            "label": f"Discord Guild {identifier}",
            "description": "Mock profile payload prepared for service-level parsing.",
            "metadata": {
                "include_related": request.include_related,
                "lookup_username": request.username,
            },
        }

    def search_content(self, request: SearchContentRequest) -> list[dict[str, object]]:
        query_token = normalize_identifier(request.query or self.settings.platform_name)
        limit = max(1, min(request.limit, 10))
        return [
            {
                "id": f"message-{index}-{query_token}",
                "url": build_resource_url(
                    self.settings.website_url,
                    "message",
                    f"message-{index}-{query_token}",
                ),
                "label": f"Discord Message {index}",
                "description": f"Search result for '{request.query}'.",
                "metadata": {
                    "query": request.query,
                    "filters": dict(request.filters),
                },
            }
            for index in range(1, limit + 1)
        ]

    def get_post_detail(self, request: GetPostDetailRequest) -> dict[str, object]:
        content_id = normalize_identifier(request.content_id or "message")
        return {
            "id": content_id,
            "url": build_resource_url(self.settings.website_url, "message", content_id),
            "label": f"Discord Message {content_id}",
            "description": "Mock detail payload prepared for parser mapping.",
            "metadata": {
                "expand_comments": request.expand_comments,
            },
        }

    def publish_content(self, request: PublishContentRequest) -> dict[str, object]:
        draft_id = normalize_identifier(request.title or "draft")
        return {
            "id": f"draft-{draft_id}",
            "url": build_resource_url(self.settings.website_url, "message", f"draft-{draft_id}"),
            "label": request.title or f"Discord Draft",
            "description": request.body,
            "metadata": {
                "visibility": request.visibility,
                "attachments": list(request.attachments),
            },
        }
