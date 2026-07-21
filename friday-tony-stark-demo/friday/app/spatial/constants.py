DEFAULT_SESSION_ID = "spatial_local_001"
DEFAULT_MODE = "hand_tracking"
DEFAULT_CAMERA_INDEX = 0
DEFAULT_FPS = 24
MIN_STREAM_FPS = 20
MAX_STREAM_FPS = 30

GESTURE_OPEN_PALM = "open_palm"
GESTURE_PINCH = "pinch"
GESTURE_GRAB = "grab"
GESTURE_IDLE = "idle"

DEFAULT_GESTURE_MAPPING = {
    "open_palm": "cancel_or_stop",
    "pinch": "select_or_grab",
    "grab": "hold_object",
    "swipe_left": "previous_panel",
    "swipe_right": "next_panel",
    "rotate": "rotate_object",
    "two_hand_expand": "explode_model",
    "reset": "reset_scene",
}
