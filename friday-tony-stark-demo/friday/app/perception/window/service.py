from __future__ import annotations

from friday.app.perception.window.command_bus import get_camera_window_command_bus
from friday.app.perception.window.intents import match_camera_window_intent
from friday.app.perception.window.schemas import (
    CameraWindowAction,
    CameraWindowCommandResult,
)


def handle_camera_window_message(message: str) -> CameraWindowCommandResult:
    match = match_camera_window_intent(message)
    if match.action == CameraWindowAction.NONE:
        return CameraWindowCommandResult(handled=False)

    if match.action == CameraWindowAction.ANALYZE:
        from friday.app.perception.service import get_perception_service

        snapshot = get_perception_service().snapshot()
        return CameraWindowCommandResult(
            handled=True,
            accepted=snapshot.status == "ready",
            action=match.action,
            message=get_perception_service().describe_scene(),
        )

    accepted = get_camera_window_command_bus().dispatch(match.action)
    if not accepted:
        return CameraWindowCommandResult(
            handled=True,
            action=match.action,
            message="The Camera Window is available when the FRIDAY desktop interface is running.",
        )
    reply = (
        "Opening the Camera Window, Boss."
        if match.action == CameraWindowAction.OPEN
        else "Closing the Camera Window, Boss."
    )
    return CameraWindowCommandResult(
        handled=True,
        accepted=True,
        action=match.action,
        message=reply,
    )
