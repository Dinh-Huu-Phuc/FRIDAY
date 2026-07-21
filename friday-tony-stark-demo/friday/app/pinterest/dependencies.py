"""Dependency factories for the Pinterest package."""

from friday.app.common.browser import BrowserGateway, BrowserManager
from friday.app.pinterest.config.settings import PinterestSettings
from friday.app.pinterest.service.client import PinterestClient
from friday.app.pinterest.service.mapper import PinterestMapper
from friday.app.pinterest.service.parser import PinterestParser
from friday.app.pinterest.service.service import PinterestService


def get_pinterest_settings() -> PinterestSettings:
    return PinterestSettings.from_env()


def get_pinterest_browser_manager(
    browser_gateway: BrowserGateway | None = None,
) -> BrowserManager:
    return BrowserManager(gateway=browser_gateway)


def get_pinterest_service(
    *,
    browser_manager: BrowserManager | None = None,
) -> PinterestService:
    settings = get_pinterest_settings()
    active_browser_manager = browser_manager or get_pinterest_browser_manager()
    client = PinterestClient(settings=settings, browser_manager=active_browser_manager)
    parser = PinterestParser()
    mapper = PinterestMapper(platform_name=settings.platform_name)
    return PinterestService(
        settings=settings,
        client=client,
        parser=parser,
        mapper=mapper,
    )
