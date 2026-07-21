from __future__ import annotations

from friday.app.spatial.service.service import get_spatial_service
from friday.core.schemas.spatial_entities import SpatialSessionState


def get_state() -> SpatialSessionState:
    return get_spatial_service().status()
