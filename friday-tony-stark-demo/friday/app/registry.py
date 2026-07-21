"""Registry and command resolution for FRIDAY social platform modules."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

from friday.app.common.browser import BrowserManager
from friday.app.facebook.constants import PLATFORM_ALIASES as FACEBOOK_ALIASES, PLATFORM_NAME as FACEBOOK_PLATFORM_NAME
from friday.app.facebook.dependencies import get_facebook_service
from friday.app.youtube.constants import PLATFORM_ALIASES as YOUTUBE_ALIASES, PLATFORM_NAME as YOUTUBE_PLATFORM_NAME
from friday.app.youtube.dependencies import get_youtube_service
from friday.app.instagram.constants import PLATFORM_ALIASES as INSTAGRAM_ALIASES, PLATFORM_NAME as INSTAGRAM_PLATFORM_NAME
from friday.app.instagram.dependencies import get_instagram_service
from friday.app.tiktok.constants import PLATFORM_ALIASES as TIKTOK_ALIASES, PLATFORM_NAME as TIKTOK_PLATFORM_NAME
from friday.app.tiktok.dependencies import get_tiktok_service
from friday.app.x.constants import PLATFORM_ALIASES as X_ALIASES, PLATFORM_NAME as X_PLATFORM_NAME
from friday.app.x.dependencies import get_x_service
from friday.app.linkedin.constants import PLATFORM_ALIASES as LINKEDIN_ALIASES, PLATFORM_NAME as LINKEDIN_PLATFORM_NAME
from friday.app.linkedin.dependencies import get_linkedin_service
from friday.app.pinterest.constants import PLATFORM_ALIASES as PINTEREST_ALIASES, PLATFORM_NAME as PINTEREST_PLATFORM_NAME
from friday.app.pinterest.dependencies import get_pinterest_service
from friday.app.reddit.constants import PLATFORM_ALIASES as REDDIT_ALIASES, PLATFORM_NAME as REDDIT_PLATFORM_NAME
from friday.app.reddit.dependencies import get_reddit_service
from friday.app.telegram.constants import PLATFORM_ALIASES as TELEGRAM_ALIASES, PLATFORM_NAME as TELEGRAM_PLATFORM_NAME
from friday.app.telegram.dependencies import get_telegram_service
from friday.app.discord.constants import PLATFORM_ALIASES as DISCORD_ALIASES, PLATFORM_NAME as DISCORD_PLATFORM_NAME
from friday.app.discord.dependencies import get_discord_service


@dataclass(slots=True, frozen=True)
class SocialPlatformEntry:
    platform_name: str
    aliases: tuple[str, ...]
    service_factory: Callable[..., Any]
    search_url_template: str


@dataclass(slots=True, frozen=True)
class SocialCommand:
    platform_name: str
    query: str = ""


SOCIAL_PLATFORM_REGISTRY: dict[str, SocialPlatformEntry] = {
    'facebook': SocialPlatformEntry(
        platform_name=FACEBOOK_PLATFORM_NAME,
        aliases=FACEBOOK_ALIASES,
        service_factory=get_facebook_service,
        search_url_template="https://www.facebook.com/search/top/?q={query}",
    ),
    'youtube': SocialPlatformEntry(
        platform_name=YOUTUBE_PLATFORM_NAME,
        aliases=YOUTUBE_ALIASES,
        service_factory=get_youtube_service,
        search_url_template="https://www.youtube.com/results?search_query={query}",
    ),
    'instagram': SocialPlatformEntry(
        platform_name=INSTAGRAM_PLATFORM_NAME,
        aliases=INSTAGRAM_ALIASES,
        service_factory=get_instagram_service,
        search_url_template="https://www.instagram.com/explore/search/keyword/?q={query}",
    ),
    'tiktok': SocialPlatformEntry(
        platform_name=TIKTOK_PLATFORM_NAME,
        aliases=TIKTOK_ALIASES,
        service_factory=get_tiktok_service,
        search_url_template="https://www.tiktok.com/search?q={query}",
    ),
    'x': SocialPlatformEntry(
        platform_name=X_PLATFORM_NAME,
        aliases=X_ALIASES,
        service_factory=get_x_service,
        search_url_template="https://x.com/search?q={query}&src=typed_query",
    ),
    'linkedin': SocialPlatformEntry(
        platform_name=LINKEDIN_PLATFORM_NAME,
        aliases=LINKEDIN_ALIASES,
        service_factory=get_linkedin_service,
        search_url_template="https://www.linkedin.com/search/results/all/?keywords={query}",
    ),
    'pinterest': SocialPlatformEntry(
        platform_name=PINTEREST_PLATFORM_NAME,
        aliases=PINTEREST_ALIASES,
        service_factory=get_pinterest_service,
        search_url_template="https://www.pinterest.com/search/pins/?q={query}",
    ),
    'reddit': SocialPlatformEntry(
        platform_name=REDDIT_PLATFORM_NAME,
        aliases=REDDIT_ALIASES,
        service_factory=get_reddit_service,
        search_url_template="https://www.reddit.com/search/?q={query}",
    ),
    'telegram': SocialPlatformEntry(
        platform_name=TELEGRAM_PLATFORM_NAME,
        aliases=TELEGRAM_ALIASES,
        service_factory=get_telegram_service,
        search_url_template="https://web.telegram.org/a/#?q={query}",
    ),
    'discord': SocialPlatformEntry(
        platform_name=DISCORD_PLATFORM_NAME,
        aliases=DISCORD_ALIASES,
        service_factory=get_discord_service,
        search_url_template="https://discord.com/channels/@me?query={query}",
    )
}

SOCIAL_OPEN_INTENT_PATTERN = re.compile(
    r"\b(open|launch|start|visit|go\s+to)\b",
    re.IGNORECASE,
)
SOCIAL_SEARCH_PATTERN = re.compile(
    r"\b(?:and\s+)?(?:search|find|look\s+up)(?:\s+for)?\s+(?P<query>.+?)\s*$",
    re.IGNORECASE,
)


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9\s]+", " ", str(value or "").strip().lower())


def resolve_social_platform(command: str) -> str | None:
    normalized = _normalize_text(command)
    if not normalized:
        return None

    tokens = set(normalized.split())
    best_match: str | None = None
    best_score = -1

    for entry in SOCIAL_PLATFORM_REGISTRY.values():
        for alias in entry.aliases:
            normalized_alias = _normalize_text(alias)
            if not normalized_alias:
                continue

            if " " in normalized_alias:
                matched = normalized_alias in normalized
            else:
                matched = normalized_alias in tokens

            if matched and len(normalized_alias) > best_score:
                best_match = entry.platform_name
                best_score = len(normalized_alias)

    return best_match


def is_social_open_request(command: str) -> bool:
    """Return whether a command requests opening a registered social platform."""
    return parse_social_command(command) is not None


def parse_social_command(command: str) -> SocialCommand | None:
    """Parse an open/search request for a registered social platform."""
    candidate = str(command or "").strip()
    platform_name = resolve_social_platform(candidate)
    search_match = SOCIAL_SEARCH_PATTERN.search(candidate)
    has_action = bool(SOCIAL_OPEN_INTENT_PATTERN.search(candidate) or search_match)
    if not candidate or not platform_name or not has_action:
        return None

    query = search_match.group("query").strip(" .,!?:;\"'") if search_match else ""
    return SocialCommand(platform_name=platform_name, query=query)


def build_social_search_url(platform_name: str, query: str) -> str:
    """Build a platform-native browser search URL for an already parsed query."""
    from urllib.parse import quote_plus

    entry = SOCIAL_PLATFORM_REGISTRY[platform_name]
    return entry.search_url_template.format(query=quote_plus(query.strip()))


def get_platform_service(
    platform_name: str,
    *,
    browser_manager: BrowserManager | None = None,
) -> Any:
    entry = SOCIAL_PLATFORM_REGISTRY[platform_name]
    return entry.service_factory(browser_manager=browser_manager)
