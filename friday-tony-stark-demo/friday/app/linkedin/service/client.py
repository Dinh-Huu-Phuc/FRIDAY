"""Low-level client for LinkedIn operations."""

from __future__ import annotations

from friday.app.common.browser import BrowserManager, TabOpenResult
from friday.app.linkedin.config.settings import LinkedInSettings
from friday.app.linkedin.schemas.requests import (
    GetPostDetailRequest,
    GetProfileRequest,
    PublishContentRequest,
    SearchContentRequest,
)
from friday.app.linkedin.utils.helpers import build_resource_url, normalize_identifier


class LinkedInClient:
    """Thin client that prepares low-level payloads for LinkedIn."""

    def __init__(
        self,
        *,
        settings: LinkedInSettings,
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
            "url": build_resource_url(self.settings.website_url, "profile", identifier),
            "label": f"LinkedIn Profile {identifier}",
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
                "id": f"post-{index}-{query_token}",
                "url": build_resource_url(
                    self.settings.website_url,
                    "post",
                    f"post-{index}-{query_token}",
                ),
                "label": f"LinkedIn Post {index}",
                "description": f"Search result for '{request.query}'.",
                "metadata": {
                    "query": request.query,
                    "filters": dict(request.filters),
                },
            }
            for index in range(1, limit + 1)
        ]

    def get_post_detail(self, request: GetPostDetailRequest) -> dict[str, object]:
        content_id = normalize_identifier(request.content_id or "post")
        return {
            "id": content_id,
            "url": build_resource_url(self.settings.website_url, "post", content_id),
            "label": f"LinkedIn Post {content_id}",
            "description": "Mock detail payload prepared for parser mapping.",
            "metadata": {
                "expand_comments": request.expand_comments,
            },
        }

    def publish_content(self, request: PublishContentRequest) -> dict[str, object]:
        draft_id = normalize_identifier(request.title or "draft")
        return {
            "id": f"draft-{draft_id}",
            "url": build_resource_url(self.settings.website_url, "post", f"draft-{draft_id}"),
            "label": request.title or f"LinkedIn Draft",
            "description": request.body,
            "metadata": {
                "visibility": request.visibility,
                "attachments": list(request.attachments),
            },
        }
