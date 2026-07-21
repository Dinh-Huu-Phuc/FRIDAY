"""Dependency factories for the LinkedIn package."""

from friday.app.common.browser import BrowserGateway, BrowserManager
from friday.app.linkedin.config.settings import LinkedInSettings
from friday.app.linkedin.service.client import LinkedInClient
from friday.app.linkedin.service.mapper import LinkedInMapper
from friday.app.linkedin.service.parser import LinkedInParser
from friday.app.linkedin.service.service import LinkedInService


def get_linkedin_settings() -> LinkedInSettings:
    return LinkedInSettings.from_env()


def get_linkedin_browser_manager(
    browser_gateway: BrowserGateway | None = None,
) -> BrowserManager:
    return BrowserManager(gateway=browser_gateway)


def get_linkedin_service(
    *,
    browser_manager: BrowserManager | None = None,
) -> LinkedInService:
    settings = get_linkedin_settings()
    active_browser_manager = browser_manager or get_linkedin_browser_manager()
    client = LinkedInClient(settings=settings, browser_manager=active_browser_manager)
    parser = LinkedInParser()
    mapper = LinkedInMapper(platform_name=settings.platform_name)
    return LinkedInService(
        settings=settings,
        client=client,
        parser=parser,
        mapper=mapper,
    )
