"""Command handlers and route-style entrypoints for Telegram."""

from friday.app.common.messages import UNKNOWN_PLATFORM_MESSAGE
from friday.app.telegram.constants import PLATFORM_ALIASES, PLATFORM_NAME
from friday.app.telegram.dependencies import get_telegram_service
from friday.app.telegram.schemas.requests import (
    GetPostDetailRequest,
    GetProfileRequest,
    OpenPlatformRequest,
    PublishContentRequest,
    SearchContentRequest,
)
from friday.app.telegram.schemas.responses import (
    ContentDetailResponse,
    ContentSearchResponse,
    OpenPlatformResponse,
    ProfileResponse,
    PublishContentResponse,
)
from friday.app.telegram.service.service import TelegramService
from friday.app.telegram.utils.helpers import matches_platform_command


def get_profile(
    request: GetProfileRequest,
    service: TelegramService | None = None,
) -> ProfileResponse:
    active_service = service or get_telegram_service()
    return active_service.get_profile(request)


def search_content(
    request: SearchContentRequest,
    service: TelegramService | None = None,
) -> ContentSearchResponse:
    active_service = service or get_telegram_service()
    return active_service.search_content(request)


def get_post_detail(
    request: GetPostDetailRequest,
    service: TelegramService | None = None,
) -> ContentDetailResponse:
    active_service = service or get_telegram_service()
    return active_service.get_post_detail(request)


def publish_content(
    request: PublishContentRequest,
    service: TelegramService | None = None,
) -> PublishContentResponse:
    active_service = service or get_telegram_service()
    return active_service.publish_content(request)


def open_platform_homepage(
    service: TelegramService | None = None,
) -> OpenPlatformResponse:
    active_service = service or get_telegram_service()
    return active_service.open_platform_homepage()


def handle_open_platform_command(
    command: str,
    service: TelegramService | None = None,
) -> OpenPlatformResponse:
    if not matches_platform_command(command, PLATFORM_ALIASES):
        return OpenPlatformResponse(
            platform=PLATFORM_NAME,
            url="",
            message=UNKNOWN_PLATFORM_MESSAGE,
            opened=False,
        )

    active_service = service or get_telegram_service()
    return active_service.open_platform_homepage(
        OpenPlatformRequest(command=command, platform=PLATFORM_NAME),
    )
