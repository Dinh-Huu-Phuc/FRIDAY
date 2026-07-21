from __future__ import annotations

from fastapi import APIRouter, HTTPException, WebSocket, status

from friday.app.spatial.exceptions import CameraUnavailableError, SpatialError, VisionDependencyError
from friday.app.spatial.service.service import get_spatial_service
from friday.app.spatial.service.spatial_socket import SpatialSocketStreamer
from friday.src.schemas.spatial.requests import SpatialModeRequest, SpatialStartRequest
from friday.src.schemas.spatial.responses import SpatialStatusResponse
from friday.src.services.spatial.service import (
    get_spatial_status,
    set_spatial_mode,
    start_spatial_session,
    stop_spatial_session,
)


router = APIRouter()


@router.post("/start", response_model=SpatialStatusResponse)
def start(payload: SpatialStartRequest) -> SpatialStatusResponse:
    try:
        state = start_spatial_session(mode=payload.mode, camera_index=payload.camera_index)
        return SpatialStatusResponse.model_validate(state.model_dump())
    except CameraUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except VisionDependencyError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except SpatialError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/stop", response_model=SpatialStatusResponse)
def stop() -> SpatialStatusResponse:
    return SpatialStatusResponse.model_validate(stop_spatial_session().model_dump())


@router.get("/status", response_model=SpatialStatusResponse)
def status_route() -> SpatialStatusResponse:
    return SpatialStatusResponse.model_validate(get_spatial_status().model_dump())


@router.post("/mode", response_model=SpatialStatusResponse)
def mode(payload: SpatialModeRequest) -> SpatialStatusResponse:
    return SpatialStatusResponse.model_validate(set_spatial_mode(payload.mode).model_dump())


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    streamer = SpatialSocketStreamer(get_spatial_service())
    await streamer.stream(websocket)
