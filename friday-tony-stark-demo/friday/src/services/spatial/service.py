from __future__ import annotations

from friday.app.spatial.exceptions import SpatialError
from friday.app.spatial.service.service import get_spatial_service
from friday.core.schemas.spatial_entities import SpatialSessionState


def start_spatial_session(*, mode: str = "hand_tracking", camera_index: int | None = None) -> SpatialSessionState:
    return get_spatial_service().start(mode=mode, camera_index=camera_index)


def stop_spatial_session() -> SpatialSessionState:
    return get_spatial_service().stop()


def get_spatial_status() -> SpatialSessionState:
    return get_spatial_service().status()


def set_spatial_mode(mode: str) -> SpatialSessionState:
    return get_spatial_service().set_mode(mode)


__all__ = [
    "SpatialError",
    "get_spatial_status",
    "set_spatial_mode",
    "start_spatial_session",
    "stop_spatial_session",
]
