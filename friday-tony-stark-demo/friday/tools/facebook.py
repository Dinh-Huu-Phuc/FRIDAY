"""Facebook Page tools backed by the FRIDAY Facebook webhook store."""

from __future__ import annotations

from friday.app.facebook.dependencies import get_facebook_service
from friday.app.facebook.schemas.requests import CheckMessagesRequest, CheckNotificationsRequest


def _trim_text(value: str, limit: int = 120) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def _format_message_summary(limit: int, unread_only: bool) -> str:
    service = get_facebook_service()
    response = service.check_messages(
        CheckMessagesRequest(limit=limit, unread_only=unread_only),
    )
    if not response.items:
        return (
            "No Facebook messages have been synchronized yet. "
            "Connect the Messenger webhook for the Facebook Page first."
        )

    lines = [f"Found {response.total} recent Facebook messages:"]
    for index, item in enumerate(response.items, start=1):
        text_preview = _trim_text(item.text or item.description or "(no content)")
        lines.append(f"{index}. {item.sender_id or 'unknown'}: {text_preview}")
    return "\n".join(lines)


def _format_notification_summary(limit: int, event_types: list[str] | None = None) -> str:
    service = get_facebook_service()
    response = service.check_notifications(
        CheckNotificationsRequest(limit=limit, event_types=event_types or []),
    )
    if not response.items:
        return (
            "No Facebook notifications have been synchronized yet. "
            "Connect the Facebook Page webhook first."
        )

    lines = [f"Found {response.total} recent Facebook notifications:"]
    for index, item in enumerate(response.items, start=1):
        description = _trim_text(item.description or item.event_type)
        lines.append(f"{index}. {item.event_type}: {description}")
    return "\n".join(lines)


def register(mcp):
    @mcp.tool()
    def check_facebook_messages(limit: int = 5, unread_only: bool = False) -> str:
        """Return the latest synchronized Facebook Page inbox messages."""
        return _format_message_summary(limit=max(1, limit), unread_only=unread_only)

    @mcp.tool()
    def check_facebook_notifications(limit: int = 5) -> str:
        """Return the latest synchronized Facebook Page notifications/events."""
        return _format_notification_summary(limit=max(1, limit))
