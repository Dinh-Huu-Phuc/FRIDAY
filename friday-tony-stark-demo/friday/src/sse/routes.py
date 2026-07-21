from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from friday.src.sse.channels import SseChannel
from friday.src.sse.manager import sse_manager


router = APIRouter()


async def _event_stream(channel: SseChannel) -> AsyncIterator[str]:
    async for event in sse_manager.subscribe(channel):
        yield event.encode()


def _stream(channel: SseChannel) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(channel),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/runtime")
def runtime_sse() -> StreamingResponse:
    return _stream("runtime")


@router.get("/agent")
def agent_sse() -> StreamingResponse:
    return _stream("agent")


@router.get("/logs")
def logs_sse() -> StreamingResponse:
    return _stream("logs")


@router.get("/rag")
def rag_sse() -> StreamingResponse:
    return _stream("rag")
