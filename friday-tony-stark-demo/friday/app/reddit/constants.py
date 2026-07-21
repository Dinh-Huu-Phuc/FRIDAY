"""Constants shared across the Reddit package."""

from friday.app.common.env import get_env_value
from friday.app.common.messages import OPEN_SUCCESS_MESSAGE, UNKNOWN_PLATFORM_MESSAGE

PLATFORM_NAME = "reddit"
PLATFORM_ALIASES = ('reddit',)
BASE_URL = "https://oauth.reddit.com"
WEBSITE_URL_ENV = "REDDIT_URL"
WEBSITE_URL = get_env_value(WEBSITE_URL_ENV, "https://reddit.com")
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RETRY_COUNT = 1
PRIMARY_RESOURCE_NAME = "subreddit"
CONTENT_RESOURCE_NAME = "post"
