"""Constants shared across the YouTube package."""

from friday.app.common.env import get_env_value
from friday.app.common.messages import OPEN_SUCCESS_MESSAGE, UNKNOWN_PLATFORM_MESSAGE

PLATFORM_NAME = "youtube"
PLATFORM_ALIASES = ('youtube', 'yt')
BASE_URL = "https://www.googleapis.com/youtube/v3"
WEBSITE_URL_ENV = "YOUTUBE_URL"
WEBSITE_URL = get_env_value(WEBSITE_URL_ENV, "https://youtube.com")
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RETRY_COUNT = 1
PRIMARY_RESOURCE_NAME = "channel"
CONTENT_RESOURCE_NAME = "video"
