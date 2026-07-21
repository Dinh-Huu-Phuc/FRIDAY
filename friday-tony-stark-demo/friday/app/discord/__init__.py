"""Discord social platform package for FRIDAY."""

from friday.app.discord.config.settings import DiscordSettings
from friday.app.discord.dependencies import get_discord_service, get_discord_settings
from friday.app.discord.service.service import DiscordService

__all__ = [
    "DiscordService",
    "DiscordSettings",
    "get_discord_service",
    "get_discord_settings",
]
