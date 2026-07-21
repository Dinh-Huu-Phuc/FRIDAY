from __future__ import annotations

from friday.app.messenger.reader import (
    ChromeProfileMessengerReader,
    ExtensionMessengerReader,
    MessengerBrowserError,
    MessengerLoginRequired,
    MessengerReader,
    PlaywrightMessengerReader,
)
from friday.app.messenger.schemas import MessengerReadResult


def check_latest_messenger_message(
    *,
    reader: MessengerReader | None = None,
) -> MessengerReadResult:
    active_reader = reader or _configured_reader()
    try:
        conversation = active_reader.read_latest()
    except MessengerLoginRequired as exc:
        return MessengerReadResult(False, str(exc), login_required=True)
    except MessengerBrowserError as exc:
        return MessengerReadResult(False, str(exc))
    except Exception as exc:
        return MessengerReadResult(
            False,
            f"I could not check Messenger. Technical error: {type(exc).__name__}.",
        )

    if conversation is None:
        return MessengerReadResult(
            True,
            "I opened Messenger, but I could not find a readable conversation preview.",
        )

    time_text = f" at {conversation.timestamp}" if conversation.timestamp else ""
    if conversation.unread:
        message = (
            f"You have a new Messenger message from {conversation.sender}{time_text}. "
            f"It says: {conversation.preview}"
        )
    else:
        message = (
            f"Your latest Messenger conversation is with {conversation.sender}{time_text}. "
            f"The latest preview says: {conversation.preview}"
        )
    return MessengerReadResult(True, message, conversation=conversation)


def _configured_reader() -> MessengerReader:
    import os

    mode = os.getenv("FRIDAY_MESSENGER_MODE", "chrome_profile").strip().lower()
    if mode == "extension":
        return ExtensionMessengerReader()
    if mode == "playwright":
        return PlaywrightMessengerReader()
    return ChromeProfileMessengerReader()
