"""Constants shared across the TikTok package."""

from friday.app.common.env import get_env_value
from friday.app.common.messages import OPEN_SUCCESS_MESSAGE, UNKNOWN_PLATFORM_MESSAGE

PLATFORM_NAME = "tiktok"
PLATFORM_ALIASES = ('tiktok', 'tik tok')
BASE_URL = "https://open.tiktokapis.com"
WEBSITE_URL_ENV = "TIKTOK_URL"
WEBSITE_URL = get_env_value(WEBSITE_URL_ENV, "https://tiktok.com")
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RETRY_COUNT = 1
PRIMARY_RESOURCE_NAME = "profile"
CONTENT_RESOURCE_NAME = "video"
