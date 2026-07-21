"""Constants shared across the Instagram package."""

from friday.app.common.env import get_env_value
from friday.app.common.messages import OPEN_SUCCESS_MESSAGE, UNKNOWN_PLATFORM_MESSAGE

PLATFORM_NAME = "instagram"
PLATFORM_ALIASES = ('instagram', 'insta')
BASE_URL = "https://graph.instagram.com"
WEBSITE_URL_ENV = "INSTAGRAM_URL"
WEBSITE_URL = get_env_value(WEBSITE_URL_ENV, "https://instagram.com")
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RETRY_COUNT = 1
PRIMARY_RESOURCE_NAME = "profile"
CONTENT_RESOURCE_NAME = "post"
