"""Dependency factories for the Facebook package."""

from friday.app.common.browser import BrowserGateway, BrowserManager
from friday.app.facebook.config.settings import FacebookSettings
from friday.app.facebook.service.client import FacebookClient
from friday.app.facebook.service.mapper import FacebookMapper
from friday.app.facebook.service.parser import FacebookParser
from friday.app.facebook.service.service import FacebookService
from friday.app.facebook.service.store import FacebookWebhookStore


def get_facebook_settings() -> FacebookSettings:
    return FacebookSettings.from_env()


def get_facebook_browser_manager(
    browser_gateway: BrowserGateway | None = None,
) -> BrowserManager:
    return BrowserManager(gateway=browser_gateway)


def get_facebook_webhook_store(
    settings: FacebookSettings | None = None,
) -> FacebookWebhookStore:
    active_settings = settings or get_facebook_settings()
    return FacebookWebhookStore(path=active_settings.webhook_store_path)


def get_facebook_service(
    *,
    browser_manager: BrowserManager | None = None,
) -> FacebookService:
    settings = get_facebook_settings()
    active_browser_manager = browser_manager or get_facebook_browser_manager()
    store = get_facebook_webhook_store(settings)
    client = FacebookClient(
        settings=settings,
        store=store,
        browser_manager=active_browser_manager,
    )
    parser = FacebookParser()
    mapper = FacebookMapper(platform_name=settings.platform_name)
    return FacebookService(
        settings=settings,
        client=client,
        parser=parser,
        mapper=mapper,
    )
