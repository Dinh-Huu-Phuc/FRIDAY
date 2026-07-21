from __future__ import annotations

from friday.app.agent_console.greeting import build_console_greeting
from friday.app.agent_console.schemas import ConsoleChatRequest
from friday.app.agent_console.service import AgentConsoleService, get_agent_console_service


def get_console_snapshot(
    *,
    session_id: str = "browser-console",
    service: AgentConsoleService | None = None,
) -> dict:
    active_service = service or get_agent_console_service()
    return active_service.get_snapshot(session_id=session_id)


def send_console_message(
    request: ConsoleChatRequest,
    *,
    service: AgentConsoleService | None = None,
) -> dict:
    active_service = service or get_agent_console_service()
    return active_service.send_message(request)


async def get_console_greeting() -> dict:
    return (await build_console_greeting()).model_dump(mode="json")
