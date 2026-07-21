"""Dependency factories for the Reddit package."""

from friday.app.common.browser import BrowserGateway, BrowserManager
from friday.app.reddit.config.settings import RedditSettings
from friday.app.reddit.service.client import RedditClient
from friday.app.reddit.service.mapper import RedditMapper
from friday.app.reddit.service.parser import RedditParser
from friday.app.reddit.service.service import RedditService


def get_reddit_settings() -> RedditSettings:
    return RedditSettings.from_env()


def get_reddit_browser_manager(
    browser_gateway: BrowserGateway | None = None,
) -> BrowserManager:
    return BrowserManager(gateway=browser_gateway)


def get_reddit_service(
    *,
    browser_manager: BrowserManager | None = None,
) -> RedditService:
    settings = get_reddit_settings()
    active_browser_manager = browser_manager or get_reddit_browser_manager()
    client = RedditClient(settings=settings, browser_manager=active_browser_manager)
    parser = RedditParser()
    mapper = RedditMapper(platform_name=settings.platform_name)
    return RedditService(
        settings=settings,
        client=client,
        parser=parser,
        mapper=mapper,
    )
