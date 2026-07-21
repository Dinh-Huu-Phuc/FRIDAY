"""Dependency factories for the YouTube package."""

from friday.app.common.browser import BrowserGateway, BrowserManager
from friday.app.youtube.config.settings import YouTubeSettings
from friday.app.youtube.service.client import YouTubeClient
from friday.app.youtube.service.mapper import YouTubeMapper
from friday.app.youtube.service.parser import YouTubeParser
from friday.app.youtube.service.service import YouTubeService


def get_youtube_settings() -> YouTubeSettings:
    return YouTubeSettings.from_env()


def get_youtube_browser_manager(
    browser_gateway: BrowserGateway | None = None,
) -> BrowserManager:
    return BrowserManager(gateway=browser_gateway)


def get_youtube_service(
    *,
    browser_manager: BrowserManager | None = None,
) -> YouTubeService:
    settings = get_youtube_settings()
    active_browser_manager = browser_manager or get_youtube_browser_manager()
    client = YouTubeClient(settings=settings, browser_manager=active_browser_manager)
    parser = YouTubeParser()
    mapper = YouTubeMapper(platform_name=settings.platform_name)
    return YouTubeService(
        settings=settings,
        client=client,
        parser=parser,
        mapper=mapper,
    )
