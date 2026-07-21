"""High-level orchestration service for Facebook."""

from __future__ import annotations

from friday.app.facebook.config.settings import FacebookSettings
from friday.app.facebook.schemas.requests import (
    CheckMessagesRequest,
    CheckNotificationsRequest,
    GetPostDetailRequest,
    GetProfileRequest,
    OpenPlatformRequest,
    PublishContentRequest,
    ReceiveWebhookRequest,
    SearchContentRequest,
    VerifyWebhookRequest,
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
from friday.app.facebook.service.client import FacebookClient
from friday.app.facebook.service.mapper import FacebookMapper
from friday.app.facebook.service.parser import FacebookParser


class FacebookService:
    """Coordinate client, parser, and mapper calls for Facebook."""

    def __init__(
        self,
        *,
        settings: FacebookSettings,
        client: FacebookClient,
        parser: FacebookParser,
        mapper: FacebookMapper,
    ) -> None:
        self.settings = settings
        self.client = client
        self.parser = parser
        self.mapper = mapper

    def open_platform_homepage(
        self,
        request: OpenPlatformRequest | None = None,
    ) -> OpenPlatformResponse:
        _ = request
        result = self.client.open_homepage()
        return self.mapper.to_open_response(
            url=result.url,
            message=result.message,
            opened=result.opened_in_new_tab,
        )

    def get_profile(self, request: GetProfileRequest) -> ProfileResponse:
        payload = self.client.get_profile(request)
        entity = self.parser.parse_page(payload)
        return self.mapper.to_profile_response(entity)

    def search_content(self, request: SearchContentRequest) -> ContentSearchResponse:
        payloads = self.client.search_content(request)
        items = [self.parser.parse_post(payload) for payload in payloads]
        return self.mapper.to_search_response(query=request.query, items=items)

    def get_post_detail(self, request: GetPostDetailRequest) -> ContentDetailResponse:
        payload = self.client.get_post_detail(request)
        entity = self.parser.parse_post(payload)
        return self.mapper.to_detail_response(entity)

    def publish_content(self, request: PublishContentRequest) -> PublishContentResponse:
        payload = self.client.publish_content(request)
        entity = self.parser.parse_post(payload)
        return self.mapper.to_publish_response(entity)

    def verify_webhook(self, request: VerifyWebhookRequest) -> WebhookVerificationResponse:
        payload = self.client.verify_webhook(request)
        return self.mapper.to_webhook_verification_response(
            verified=bool(payload["verified"]),
            challenge=str(payload["challenge"]),
            message=str(payload["message"]),
        )

    def ingest_webhook(self, request: ReceiveWebhookRequest) -> WebhookIngestResponse:
        payload = self.client.ingest_webhook(request)
        message_items = [self.parser.parse_message(item) for item in payload["messages"]]
        notification_items = [self.parser.parse_notification(item) for item in payload["notifications"]]
        event_items = [self.parser.parse_webhook_event(item) for item in payload["events"]]
        self.client.persist_webhook_records(
            messages=payload["messages"],
            notifications=payload["notifications"],
            events=payload["events"],
        )
        return self.mapper.to_webhook_ingest_response(
            accepted=bool(payload["accepted"]),
            stored_event_count=len(event_items),
            stored_message_count=len(message_items),
            stored_notification_count=len(notification_items),
            events=event_items,
            message=str(payload["message"]),
        )

    def check_messages(self, request: CheckMessagesRequest) -> MessageListResponse:
        payloads = self.client.list_messages(request)
        items = [self.parser.parse_message(payload) for payload in payloads]
        message = (
            f"Facebook Page inbox has {len(items)} synchronized messages."
            if items
            else "No Facebook Page messages have been synchronized yet."
        )
        return self.mapper.to_message_list_response(items=items, message=message)

    def check_notifications(self, request: CheckNotificationsRequest) -> NotificationListResponse:
        payloads = self.client.list_notifications(request)
        items = [self.parser.parse_notification(payload) for payload in payloads]
        message = (
            f"Facebook Page notifications has {len(items)} synchronized events."
            if items
            else "No Facebook Page notifications have been synchronized yet."
        )
        return self.mapper.to_notification_list_response(items=items, message=message)
