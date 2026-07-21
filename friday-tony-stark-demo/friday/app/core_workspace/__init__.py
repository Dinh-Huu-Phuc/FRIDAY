"""Safe workspace adapter for the user-facing Core AI."""

from .schemas import (
    WorkspaceIndexRequest,
    WorkspaceIndexResponse,
    WorkspaceReadRequest,
    WorkspaceReadResponse,
    WorkspaceSearchRequest,
    WorkspaceSearchResponse,
)
from .service import build_workspace_context, index_workspace, read_workspace_file, search_workspace

__all__ = [
    "WorkspaceIndexRequest",
    "WorkspaceIndexResponse",
    "WorkspaceReadRequest",
    "WorkspaceReadResponse",
    "WorkspaceSearchRequest",
    "WorkspaceSearchResponse",
    "build_workspace_context",
    "index_workspace",
    "read_workspace_file",
    "search_workspace",
]
