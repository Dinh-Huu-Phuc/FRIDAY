from __future__ import annotations

from fastapi import APIRouter


router = APIRouter()


@router.get("")
def health() -> dict[str, str | bool]:
    return {"ok": True, "status": "healthy"}


@router.get("/live")
def live() -> dict[str, str | bool]:
    return {"ok": True, "status": "live"}


@router.get("/ready")
def ready() -> dict[str, str | bool]:
    return {"ok": True, "status": "ready"}
