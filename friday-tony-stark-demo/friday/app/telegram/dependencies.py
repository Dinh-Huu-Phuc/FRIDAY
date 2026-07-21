"""Dependency factories for the Telegram package."""

from friday.app.common.browser import BrowserGateway, BrowserManager
from friday.app.telegram.config.settings import TelegramSettings
from friday.app.telegram.service.client import TelegramClient
from friday.app.telegram.service.mapper import TelegramMapper
from friday.app.telegram.service.parser import TelegramParser
from friday.app.telegram.service.service import TelegramService


def get_telegram_settings() -> TelegramSettings:
    return TelegramSettings.from_env()


def get_telegram_browser_manager(
    browser_gateway: BrowserGateway | None = None,
) -> BrowserManager:
    return BrowserManager(gateway=browser_gateway)


def get_telegram_service(
    *,
    browser_manager: BrowserManager | None = None,
) -> TelegramService:
    settings = get_telegram_settings()
    active_browser_manager = browser_manager or get_telegram_browser_manager()
    client = TelegramClient(settings=settings, browser_manager=active_browser_manager)
    parser = TelegramParser()
    mapper = TelegramMapper(platform_name=settings.platform_name)
    return TelegramService(
        settings=settings,
        client=client,
        parser=parser,
        mapper=mapper,
    )
