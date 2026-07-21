from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MessengerConversationPreview:
    sender: str
    preview: str
    timestamp: str = ""
    unread: bool = False
    url: str = ""


@dataclass(slots=True, frozen=True)
class MessengerReadResult:
    ok: bool
    message: str
    conversation: MessengerConversationPreview | None = None
    login_required: bool = False
