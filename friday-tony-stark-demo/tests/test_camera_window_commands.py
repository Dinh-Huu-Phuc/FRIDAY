from friday.app.perception.window import (
    CameraWindowAction,
    get_camera_window_command_bus,
    handle_camera_window_message,
    match_camera_window_intent,
)


def test_camera_window_intents_support_open_and_close_phrases() -> None:
    assert match_camera_window_intent("FRIDAY, open camera.").action == CameraWindowAction.OPEN
    assert match_camera_window_intent("FRIDAY Agent, open the camera.").action == CameraWindowAction.OPEN
    assert match_camera_window_intent("FRIDAY, launch camera.").action == CameraWindowAction.OPEN
    assert match_camera_window_intent("Show webcam.").action == CameraWindowAction.OPEN
    assert match_camera_window_intent("FRIDAY close camera window").action == CameraWindowAction.CLOSE
    assert match_camera_window_intent("take a picture").action == CameraWindowAction.NONE


def test_camera_window_intents_support_scene_analysis() -> None:
    assert (
        match_camera_window_intent("FRIDAY, analyze camera.").action
        == CameraWindowAction.ANALYZE
    )
    assert (
        match_camera_window_intent("What do you see through the camera?").action
        == CameraWindowAction.ANALYZE
    )


def test_camera_window_handler_dispatches_to_desktop_subscriber() -> None:
    received: list[CameraWindowAction] = []
    unsubscribe = get_camera_window_command_bus().subscribe(received.append)
    try:
        result = handle_camera_window_message("FRIDAY, open camera.")
    finally:
        unsubscribe()

    assert result.handled is True
    assert result.accepted is True
    assert received == [CameraWindowAction.OPEN]
