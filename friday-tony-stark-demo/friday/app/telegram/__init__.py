"""Telegram social platform package for FRIDAY."""

from friday.app.telegram.config.settings import TelegramSettings
from friday.app.telegram.dependencies import get_telegram_service, get_telegram_settings
from friday.app.telegram.service.service import TelegramService

__all__ = [
    "TelegramService",
    "TelegramSettings",
    "get_telegram_service",
    "get_telegram_settings",
]
