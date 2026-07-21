"""Constants shared across the Pinterest package."""

from friday.app.common.env import get_env_value
from friday.app.common.messages import OPEN_SUCCESS_MESSAGE, UNKNOWN_PLATFORM_MESSAGE

PLATFORM_NAME = "pinterest"
PLATFORM_ALIASES = ('pinterest',)
BASE_URL = "https://api.pinterest.com/v5"
WEBSITE_URL_ENV = "PINTEREST_URL"
WEBSITE_URL = get_env_value(WEBSITE_URL_ENV, "https://pinterest.com")
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RETRY_COUNT = 1
PRIMARY_RESOURCE_NAME = "profile"
CONTENT_RESOURCE_NAME = "pin"
