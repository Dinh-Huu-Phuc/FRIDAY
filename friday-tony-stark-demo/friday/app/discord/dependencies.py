"""Dependency factories for the Discord package."""

from friday.app.common.browser import BrowserGateway, BrowserManager
from friday.app.discord.config.settings import DiscordSettings
from friday.app.discord.service.client import DiscordClient
from friday.app.discord.service.mapper import DiscordMapper
from friday.app.discord.service.parser import DiscordParser
from friday.app.discord.service.service import DiscordService


def get_discord_settings() -> DiscordSettings:
    return DiscordSettings.from_env()


def get_discord_browser_manager(
    browser_gateway: BrowserGateway | None = None,
) -> BrowserManager:
    return BrowserManager(gateway=browser_gateway)


def get_discord_service(
    *,
    browser_manager: BrowserManager | None = None,
) -> DiscordService:
    settings = get_discord_settings()
    active_browser_manager = browser_manager or get_discord_browser_manager()
    client = DiscordClient(settings=settings, browser_manager=active_browser_manager)
    parser = DiscordParser()
    mapper = DiscordMapper(platform_name=settings.platform_name)
    return DiscordService(
        settings=settings,
        client=client,
        parser=parser,
        mapper=mapper,
    )
