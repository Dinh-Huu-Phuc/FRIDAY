"""Command handlers and route-style entrypoints for Facebook."""

from friday.app.common.messages import UNKNOWN_PLATFORM_MESSAGE
from friday.app.facebook.constants import PLATFORM_ALIASES, PLATFORM_NAME
from friday.app.facebook.dependencies import get_facebook_service
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
from friday.app.facebook.service.service import FacebookService
from friday.app.facebook.utils.helpers import matches_platform_command


def get_profile(
    request: GetProfileRequest,
    service: FacebookService | None = None,
) -> ProfileResponse:
    active_service = service or get_facebook_service()
    return active_service.get_profile(request)


def search_content(
    request: SearchContentRequest,
    service: FacebookService | None = None,
) -> ContentSearchResponse:
    active_service = service or get_facebook_service()
    return active_service.search_content(request)


def get_post_detail(
    request: GetPostDetailRequest,
    service: FacebookService | None = None,
) -> ContentDetailResponse:
    active_service = service or get_facebook_service()
    return active_service.get_post_detail(request)


def publish_content(
    request: PublishContentRequest,
    service: FacebookService | None = None,
) -> PublishContentResponse:
    active_service = service or get_facebook_service()
    return active_service.publish_content(request)


def open_platform_homepage(
    service: FacebookService | None = None,
) -> OpenPlatformResponse:
    active_service = service or get_facebook_service()
    return active_service.open_platform_homepage()


def handle_open_platform_command(
    command: str,
    service: FacebookService | None = None,
) -> OpenPlatformResponse:
    if not matches_platform_command(command, PLATFORM_ALIASES):
        return OpenPlatformResponse(
            platform=PLATFORM_NAME,
            url="",
            message=UNKNOWN_PLATFORM_MESSAGE,
            opened=False,
        )

    active_service = service or get_facebook_service()
    return active_service.open_platform_homepage(
        OpenPlatformRequest(command=command, platform=PLATFORM_NAME),
    )


def verify_webhook_subscription(
    request: VerifyWebhookRequest,
    service: FacebookService | None = None,
) -> WebhookVerificationResponse:
    active_service = service or get_facebook_service()
    return active_service.verify_webhook(request)


def receive_messenger_webhook(
    request: ReceiveWebhookRequest,
    service: FacebookService | None = None,
) -> WebhookIngestResponse:
    active_service = service or get_facebook_service()
    return active_service.ingest_webhook(request)


def check_messages(
    request: CheckMessagesRequest | None = None,
    service: FacebookService | None = None,
) -> MessageListResponse:
    active_service = service or get_facebook_service()
    active_request = request or CheckMessagesRequest()
    return active_service.check_messages(active_request)


def check_notifications(
    request: CheckNotificationsRequest | None = None,
    service: FacebookService | None = None,
) -> NotificationListResponse:
    active_service = service or get_facebook_service()
    active_request = request or CheckNotificationsRequest()
    return active_service.check_notifications(active_request)
