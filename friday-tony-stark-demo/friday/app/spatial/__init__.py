from __future__ import annotations


def get_spatial_service():
    from friday.app.spatial.service.service import get_spatial_service as resolve

    return resolve()

__all__ = ["get_spatial_service"]
