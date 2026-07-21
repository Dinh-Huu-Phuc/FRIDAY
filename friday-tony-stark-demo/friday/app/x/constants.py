"""Constants shared across the X package."""

from friday.app.common.env import get_env_value
from friday.app.common.messages import OPEN_SUCCESS_MESSAGE, UNKNOWN_PLATFORM_MESSAGE

PLATFORM_NAME = "x"
PLATFORM_ALIASES = ('x', 'twitter')
BASE_URL = "https://api.x.com/2"
WEBSITE_URL_ENV = "X_URL"
WEBSITE_URL = get_env_value(WEBSITE_URL_ENV, "https://x.com")
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RETRY_COUNT = 1
PRIMARY_RESOURCE_NAME = "account"
CONTENT_RESOURCE_NAME = "tweet"
