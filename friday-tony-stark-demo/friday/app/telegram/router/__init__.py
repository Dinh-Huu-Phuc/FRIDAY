"""Route exports for the Telegram package."""

from friday.app.telegram.router.routes import (
    get_profile,
    get_post_detail,
    handle_open_platform_command,
    open_platform_homepage,
    publish_content,
    search_content,
)

__all__ = [
    "get_profile",
    "get_post_detail",
    "handle_open_platform_command",
    "open_platform_homepage",
    "publish_content",
    "search_content",
]
