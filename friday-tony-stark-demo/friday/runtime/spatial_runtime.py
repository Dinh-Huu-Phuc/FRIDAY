from __future__ import annotations

from friday.app.spatial.service.service import get_spatial_service
from friday.core.schemas.spatial_entities import SpatialSessionState
from friday.runtime.spatial_policy import gesture_mapping


def enable(mode: str = "hand_tracking") -> SpatialSessionState:
    return get_spatial_service().start(mode=mode)


def disable() -> SpatialSessionState:
    return get_spatial_service().stop()


def set_mode(mode: str) -> SpatialSessionState:
    return get_spatial_service().set_mode(mode)


def status() -> dict[str, object]:
    state = get_spatial_service().status()
    return {**state.model_dump(), "gesture_mapping": gesture_mapping()}
