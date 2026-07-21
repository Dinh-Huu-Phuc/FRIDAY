from __future__ import annotations

from pydantic import BaseModel, Field


class SpatialPosition(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    z: float = 0.0


class FingerState(BaseModel):
    thumb: bool = False
    index: bool = False
    middle: bool = False
    ring: bool = False
    pinky: bool = False


class SpatialGestureEvent(BaseModel):
    type: str = "spatial.gesture"
    session_id: str
    mode: str
    gesture: str
    hand: str = "unknown"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    position: SpatialPosition
    fingers: FingerState
    timestamp: int


class SpatialSessionState(BaseModel):
    session_id: str
    enabled: bool = False
    mode: str = "hand_tracking"
    camera_index: int = 0
    fps: int = 24
    last_gesture: str | None = None
    last_error: str | None = None
