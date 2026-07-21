"""Constants shared across the LinkedIn package."""

from friday.app.common.env import get_env_value
from friday.app.common.messages import OPEN_SUCCESS_MESSAGE, UNKNOWN_PLATFORM_MESSAGE

PLATFORM_NAME = "linkedin"
PLATFORM_ALIASES = ('linkedin', 'linked in')
BASE_URL = "https://api.linkedin.com/v2"
WEBSITE_URL_ENV = "LINKEDIN_URL"
WEBSITE_URL = get_env_value(WEBSITE_URL_ENV, "https://linkedin.com")
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RETRY_COUNT = 1
PRIMARY_RESOURCE_NAME = "profile"
CONTENT_RESOURCE_NAME = "post"
