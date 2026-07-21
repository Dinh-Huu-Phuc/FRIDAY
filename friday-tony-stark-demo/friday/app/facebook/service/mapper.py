"""Response mapper for Facebook."""

from __future__ import annotations

from friday.app.facebook.schemas.entities import (
    FacebookMessageEntity,
    FacebookNotificationEntity,
    FacebookPageEntity,
    FacebookPostEntity,
    FacebookWebhookEventEntity,
)
from friday.app.facebook.schemas.responses import (
    ContentDetailResponse,
    ContentSearchResponse,
    MessageListResponse,
    NotificationListResponse,
    OpenPlatformResponse,
    ProfileResponse,
    PublishContentResponse,
    WebhookIngestResponse,
    WebhookVerificationResponse,
)


class FacebookMapper:
    """Map Facebook domain entities into outward-facing responses."""

    def __init__(self, *, platform_name: str) -> None:
        self.platform_name = platform_name

    def to_open_response(self, *, url: str, message: str, opened: bool) -> OpenPlatformResponse:
        return OpenPlatformResponse(
            platform=self.platform_name,
            url=url,
            message=message,
            opened=opened,
        )

    def to_profile_response(self, entity: FacebookPageEntity) -> ProfileResponse:
        return ProfileResponse(platform=self.platform_name, profile=entity)

    def to_search_response(
        self,
        *,
        query: str,
        items: list[FacebookPostEntity],
    ) -> ContentSearchResponse:
        return ContentSearchResponse(
            platform=self.platform_name,
            query=query,
            items=items,
        )

    def to_detail_response(self, entity: FacebookPostEntity) -> ContentDetailResponse:
        return ContentDetailResponse(platform=self.platform_name, item=entity)

    def to_publish_response(self, entity: FacebookPostEntity) -> PublishContentResponse:
        return PublishContentResponse(platform=self.platform_name, item=entity)

    def to_webhook_verification_response(
        self,
        *,
        verified: bool,
        challenge: str,
        message: str,
    ) -> WebhookVerificationResponse:
        return WebhookVerificationResponse(
            verified=verified,
            challenge=challenge,
            message=message,
        )

    def to_webhook_ingest_response(
        self,
        *,
        accepted: bool,
        stored_event_count: int,
        stored_message_count: int,
        stored_notification_count: int,
        events: list[FacebookWebhookEventEntity],
        message: str,
    ) -> WebhookIngestResponse:
        return WebhookIngestResponse(
            platform=self.platform_name,
            accepted=accepted,
            stored_event_count=stored_event_count,
            stored_message_count=stored_message_count,
            stored_notification_count=stored_notification_count,
            events=events,
            message=message,
        )

    def to_message_list_response(
        self,
        *,
        items: list[FacebookMessageEntity],
        message: str,
    ) -> MessageListResponse:
        return MessageListResponse(
            platform=self.platform_name,
            items=items,
            total=len(items),
            message=message,
        )

    def to_notification_list_response(
        self,
        *,
        items: list[FacebookNotificationEntity],
        message: str,
    ) -> NotificationListResponse:
        return NotificationListResponse(
            platform=self.platform_name,
            items=items,
            total=len(items),
            message=message,
        )
