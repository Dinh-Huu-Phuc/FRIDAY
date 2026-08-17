from dataclasses import dataclass

from friday.app.perception.camera.settings import get_default_camera_index
from friday.app.spatial.constants import DEFAULT_FPS, DEFAULT_MODE, DEFAULT_SESSION_ID


@dataclass(frozen=True)
class SpatialConfig:
    session_id: str = DEFAULT_SESSION_ID
    mode: str = DEFAULT_MODE
    camera_index: int = 0
    fps: int = DEFAULT_FPS


def get_spatial_config() -> SpatialConfig:
    return SpatialConfig(camera_index=get_default_camera_index())
