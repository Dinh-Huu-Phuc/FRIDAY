from __future__ import annotations

import asyncio

from fastapi import APIRouter, Header, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from friday.app.agent_console.schemas import ConsoleChatRequest
from friday.app.agent_console.tts_service import synthesize_console_speech
from friday.gmail_system_agent import check_unread_gmail_with_timeout, format_gmail_report
from friday.src.router.v1.agent.workspace_routes import router as workspace_router
from friday.src.services.agent.service import chat, console, greeting
from friday.src.services.agent.stt_service import SpeechTranscriptionError, transcribe_core_audio


router = APIRouter()
router.include_router(workspace_router)


class AgentTtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    provider: str = "auto"


class AgentGmailCheckRequest(BaseModel):
    include_locally_reported: bool = False


@router.post("/chat")
async def agent_chat(payload: ConsoleChatRequest) -> dict:
    return await chat(payload)


@router.get("/console")
async def agent_console() -> dict:
    return console()


@router.get("/greeting")
async def agent_greeting() -> dict:
    return await greeting()


@router.post("/tts")
async def agent_tts(payload: AgentTtsRequest) -> Response:
    audio = await synthesize_console_speech(payload.text, provider=payload.provider)
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/stt")
async def agent_stt(
    request: Request,
    content_type: str = Header(default="audio/webm"),
    x_stt_language: str = Header(default="en"),
) -> dict:
    try:
        result = await transcribe_core_audio(
            await request.body(),
            content_type=content_type,
            language=x_stt_language,
        )
    except SpeechTranscriptionError as exc:
        return {
            "ok": False,
            "message": str(exc),
            "raw_text": "",
            "refined_text": "",
        }

    return {
        "ok": True,
        **result.to_dict(),
    }


@router.post("/gmail/check-unread")
async def agent_gmail_check_unread(payload: AgentGmailCheckRequest | None = None) -> dict:
    result = await check_unread_gmail_with_timeout(
        include_locally_reported=bool(payload.include_locally_reported) if payload else False,
    )
    return {
        "ok": result.ok,
        "message": result.message,
        "report": format_gmail_report(result),
        "unread_count": result.unread_count,
        "reported_count": result.reported_count,
        "skipped_count": result.skipped_count,
        "log_path": result.log_path,
        "error": result.error,
        "messages": [
            {
                "message_id": message.message_id,
                "thread_id": message.thread_id,
                "from": message.sender,
                "subject": message.subject,
                "date": message.date,
                "snippet": message.snippet,
                "body_preview": message.body_preview,
                "already_reported": message.already_reported,
            }
            for message in result.messages
        ],
    }
