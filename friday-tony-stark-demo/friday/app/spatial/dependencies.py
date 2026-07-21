from friday.app.spatial.service.service import SpatialService, get_spatial_service


def get_spatial_engine() -> SpatialService:
    return get_spatial_service()
