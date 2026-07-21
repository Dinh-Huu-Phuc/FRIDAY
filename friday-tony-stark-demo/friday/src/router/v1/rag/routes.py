from __future__ import annotations

from fastapi import APIRouter

from friday.src.schemas.rag.requests import RagIndexBuildRequest, RagQueryRequest
from friday.src.schemas.rag.responses import RagIndexBuildResponse, RagQueryResponse
from friday.src.services.rag.service import build_index, query


router = APIRouter()


@router.post("/query", response_model=RagQueryResponse)
def rag_query(payload: RagQueryRequest) -> RagQueryResponse:
    return query(payload)


@router.post("/index/build", response_model=RagIndexBuildResponse)
def rag_index_build(payload: RagIndexBuildRequest) -> RagIndexBuildResponse:
    return build_index(payload)
