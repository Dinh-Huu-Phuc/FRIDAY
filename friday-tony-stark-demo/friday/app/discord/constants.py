"""Constants shared across the Discord package."""

from friday.app.common.env import get_env_value
from friday.app.common.messages import OPEN_SUCCESS_MESSAGE, UNKNOWN_PLATFORM_MESSAGE

PLATFORM_NAME = "discord"
PLATFORM_ALIASES = ('discord',)
BASE_URL = "https://discord.com/api/v10"
WEBSITE_URL_ENV = "DISCORD_URL"
WEBSITE_URL = get_env_value(WEBSITE_URL_ENV, "https://discord.com/app")
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RETRY_COUNT = 1
PRIMARY_RESOURCE_NAME = "guild"
CONTENT_RESOURCE_NAME = "message"
