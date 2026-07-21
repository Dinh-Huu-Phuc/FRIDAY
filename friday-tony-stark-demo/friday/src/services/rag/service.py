from __future__ import annotations

from friday.src.schemas.rag.requests import RagIndexBuildRequest, RagQueryRequest
from friday.src.schemas.rag.responses import RagIndexBuildResponse, RagQueryResponse


def query(payload: RagQueryRequest) -> RagQueryResponse:
    return RagQueryResponse(query=payload.query, results=[])


def build_index(payload: RagIndexBuildRequest) -> RagIndexBuildResponse:
    source = payload.source or "default"
    return RagIndexBuildResponse(status="queued", message=f"RAG index build requested for {source}.")
