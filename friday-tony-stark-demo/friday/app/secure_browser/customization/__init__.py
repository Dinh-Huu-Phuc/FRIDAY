from friday.app.secure_browser.customization.google_search import (
    GOOGLE_SEARCH_BRAND_SCRIPT_NAME,
    build_google_search_brand_script,
    install_google_search_branding,
    is_google_search_url,
)
from friday.app.secure_browser.customization.platform_video import (
    PLATFORM_VIDEO_SCRIPT_NAME,
    build_platform_video_script,
    install_platform_video_selection,
)


def install_browser_customizations(profile) -> None:
    install_google_search_branding(profile)
    install_platform_video_selection(profile)

__all__ = [
    "GOOGLE_SEARCH_BRAND_SCRIPT_NAME",
    "PLATFORM_VIDEO_SCRIPT_NAME",
    "build_google_search_brand_script",
    "build_platform_video_script",
    "install_browser_customizations",
    "install_google_search_branding",
    "install_platform_video_selection",
    "is_google_search_url",
]
