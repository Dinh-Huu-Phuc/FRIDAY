from __future__ import annotations

from fastapi import APIRouter

from friday.app.core_workspace import (
    WorkspaceIndexRequest,
    WorkspaceIndexResponse,
    WorkspaceReadRequest,
    WorkspaceReadResponse,
    WorkspaceSearchRequest,
    WorkspaceSearchResponse,
    index_workspace,
    read_workspace_file,
    search_workspace,
)


router = APIRouter()


@router.post("/workspace/index")
async def workspace_index(payload: WorkspaceIndexRequest) -> WorkspaceIndexResponse:
    return index_workspace(max_files=payload.max_files)


@router.post("/workspace/read")
async def workspace_read(payload: WorkspaceReadRequest) -> WorkspaceReadResponse:
    return read_workspace_file(path=payload.path, max_chars=payload.max_chars)


@router.post("/workspace/search")
async def workspace_search(payload: WorkspaceSearchRequest) -> WorkspaceSearchResponse:
    return search_workspace(
        query=payload.query,
        max_results=payload.max_results,
        max_chars_per_match=payload.max_chars_per_match,
    )
