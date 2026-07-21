from dataclasses import dataclass

from friday.app.spatial.constants import DEFAULT_CAMERA_INDEX, DEFAULT_FPS, DEFAULT_MODE, DEFAULT_SESSION_ID


@dataclass(frozen=True)
class SpatialConfig:
    session_id: str = DEFAULT_SESSION_ID
    mode: str = DEFAULT_MODE
    camera_index: int = DEFAULT_CAMERA_INDEX
    fps: int = DEFAULT_FPS


def get_spatial_config() -> SpatialConfig:
    return SpatialConfig()
