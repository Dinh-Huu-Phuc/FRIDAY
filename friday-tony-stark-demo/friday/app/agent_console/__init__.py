"""Browser console support for the FRIDAY dashboard."""

from .routes import get_console_greeting, get_console_snapshot, send_console_message

__all__ = ["get_console_greeting", "get_console_snapshot", "send_console_message"]
