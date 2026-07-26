from __future__ import annotations

from friday.app.code_map.command_bus import get_code_map_command_bus
from friday.app.code_map.intents import match_code_map_intent
from friday.app.code_map.schemas import CodeMapAction, CodeMapCommandResult
from friday.app.code_map.settings import get_code_map_settings


def handle_code_map_message(message: str) -> CodeMapCommandResult:
    match = match_code_map_intent(message)
    if match.action == CodeMapAction.NONE:
        return CodeMapCommandResult(handled=False)

    if not get_code_map_settings().enabled:
        return CodeMapCommandResult(
            handled=True,
            action=match.action,
            message="The Code Map is disabled in FRIDAY settings, Boss.",
        )

    accepted = get_code_map_command_bus().dispatch(match.action)
    if not accepted:
        return CodeMapCommandResult(
            handled=True,
            action=match.action,
            message="The Code Map is available when the FRIDAY desktop interface is running.",
        )

    message_text = (
        "Opening the Code Map, Boss."
        if match.action == CodeMapAction.OPEN
        else "Closing the Code Map, Boss."
    )
    return CodeMapCommandResult(
        handled=True,
        accepted=True,
        action=match.action,
        message=message_text,
    )
