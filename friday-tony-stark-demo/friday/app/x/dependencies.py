"""Dependency factories for the X package."""

from friday.app.common.browser import BrowserGateway, BrowserManager
from friday.app.x.config.settings import XSettings
from friday.app.x.service.client import XClient
from friday.app.x.service.mapper import XMapper
from friday.app.x.service.parser import XParser
from friday.app.x.service.service import XService


def get_x_settings() -> XSettings:
    return XSettings.from_env()


def get_x_browser_manager(
    browser_gateway: BrowserGateway | None = None,
) -> BrowserManager:
    return BrowserManager(gateway=browser_gateway)


def get_x_service(
    *,
    browser_manager: BrowserManager | None = None,
) -> XService:
    settings = get_x_settings()
    active_browser_manager = browser_manager or get_x_browser_manager()
    client = XClient(settings=settings, browser_manager=active_browser_manager)
    parser = XParser()
    mapper = XMapper(platform_name=settings.platform_name)
    return XService(
        settings=settings,
        client=client,
        parser=parser,
        mapper=mapper,
    )
