from __future__ import annotations

from fastapi import APIRouter

from friday.app.windows_launcher.schemas import (
    AppLaunchResponse,
    AppOpenRequest,
    AppSearchRequest,
    AppSearchResponse,
)
from friday.app.windows_launcher.service import open_app, search_apps


router = APIRouter()


@router.post("/apps/search", response_model=AppSearchResponse)
def search_windows_apps(payload: AppSearchRequest) -> AppSearchResponse:
    return search_apps(query=payload.query, limit=payload.limit)


@router.post("/apps/open", response_model=AppLaunchResponse)
def open_windows_app(payload: AppOpenRequest) -> AppLaunchResponse:
    return open_app(
        query=payload.query,
        app_id=payload.app_id,
        path=payload.path,
        min_score=payload.min_score,
    )
