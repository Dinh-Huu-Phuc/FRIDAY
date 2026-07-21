"""Dependency factories for the Instagram package."""

from friday.app.common.browser import BrowserGateway, BrowserManager
from friday.app.instagram.config.settings import InstagramSettings
from friday.app.instagram.service.client import InstagramClient
from friday.app.instagram.service.mapper import InstagramMapper
from friday.app.instagram.service.parser import InstagramParser
from friday.app.instagram.service.service import InstagramService


def get_instagram_settings() -> InstagramSettings:
    return InstagramSettings.from_env()


def get_instagram_browser_manager(
    browser_gateway: BrowserGateway | None = None,
) -> BrowserManager:
    return BrowserManager(gateway=browser_gateway)


def get_instagram_service(
    *,
    browser_manager: BrowserManager | None = None,
) -> InstagramService:
    settings = get_instagram_settings()
    active_browser_manager = browser_manager or get_instagram_browser_manager()
    client = InstagramClient(settings=settings, browser_manager=active_browser_manager)
    parser = InstagramParser()
    mapper = InstagramMapper(platform_name=settings.platform_name)
    return InstagramService(
        settings=settings,
        client=client,
        parser=parser,
        mapper=mapper,
    )
