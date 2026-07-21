"""Constants shared across the Telegram package."""

from friday.app.common.env import get_env_value
from friday.app.common.messages import OPEN_SUCCESS_MESSAGE, UNKNOWN_PLATFORM_MESSAGE

PLATFORM_NAME = "telegram"
PLATFORM_ALIASES = ('telegram',)
BASE_URL = "https://api.telegram.org"
WEBSITE_URL_ENV = "TELEGRAM_URL"
WEBSITE_URL = get_env_value(WEBSITE_URL_ENV, "https://web.telegram.org")
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RETRY_COUNT = 1
PRIMARY_RESOURCE_NAME = "chat"
CONTENT_RESOURCE_NAME = "message"
