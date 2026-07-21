from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, status

from friday.app.messenger.bridge import MessengerExtensionBridge


router = APIRouter()
bridge = MessengerExtensionBridge()


@router.get("/messenger/command")
def get_messenger_command() -> dict[str, Any]:
    return {"ok": True, "command": bridge.pending_command()}


@router.post("/messenger/snapshot")
def submit_messenger_snapshot(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    conversations = payload.get("conversations")
    if not isinstance(conversations, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="conversations must be a list",
        )
    accepted = bridge.submit_snapshot(
        request_id=str(payload.get("request_id") or ""),
        conversations=[item for item in conversations if isinstance(item, dict)],
        page_url=str(payload.get("page_url") or ""),
    )
    if not accepted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No matching Messenger scan is pending",
        )
    return {"ok": True, "accepted": True}
