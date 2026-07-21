"""Dependency factories for the TikTok package."""

from friday.app.common.browser import BrowserGateway, BrowserManager
from friday.app.tiktok.config.settings import TikTokSettings
from friday.app.tiktok.service.client import TikTokClient
from friday.app.tiktok.service.mapper import TikTokMapper
from friday.app.tiktok.service.parser import TikTokParser
from friday.app.tiktok.service.service import TikTokService


def get_tiktok_settings() -> TikTokSettings:
    return TikTokSettings.from_env()


def get_tiktok_browser_manager(
    browser_gateway: BrowserGateway | None = None,
) -> BrowserManager:
    return BrowserManager(gateway=browser_gateway)


def get_tiktok_service(
    *,
    browser_manager: BrowserManager | None = None,
) -> TikTokService:
    settings = get_tiktok_settings()
    active_browser_manager = browser_manager or get_tiktok_browser_manager()
    client = TikTokClient(settings=settings, browser_manager=active_browser_manager)
    parser = TikTokParser()
    mapper = TikTokMapper(platform_name=settings.platform_name)
    return TikTokService(
        settings=settings,
        client=client,
        parser=parser,
        mapper=mapper,
    )
