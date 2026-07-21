from __future__ import annotations

import time

from friday.app.spatial.constants import DEFAULT_MODE, GESTURE_IDLE
from friday.app.spatial.exceptions import SpatialError
from friday.app.spatial.service.camera_service import CameraService
from friday.app.spatial.service.coordinate_mapper import CoordinateMapper
from friday.app.spatial.service.gesture_engine import GestureEngine
from friday.app.spatial.service.hand_tracker import HandTracker
from friday.app.spatial.service.spatial_session import SpatialSession
from friday.core.schemas.spatial_entities import FingerState, SpatialGestureEvent, SpatialPosition, SpatialSessionState


class SpatialService:
    def __init__(self) -> None:
        self.session = SpatialSession()
        self.camera = CameraService()
        self.mapper = CoordinateMapper()
        self.tracker = HandTracker(self.mapper)
        self.gestures = GestureEngine()

    def start(self, *, mode: str = DEFAULT_MODE, camera_index: int | None = None) -> SpatialSessionState:
        target_state = self.session.snapshot()
        target_index = target_state.camera_index if camera_index is None else camera_index
        try:
            self.camera.open(target_index)
        except SpatialError as exc:
            self.session.record_error(str(exc))
            raise
        return self.session.start(mode=mode, camera_index=target_index)

    def stop(self) -> SpatialSessionState:
        self.camera.stop()
        self.tracker.close()
        return self.session.stop()

    def status(self) -> SpatialSessionState:
        return self.session.snapshot()

    def set_mode(self, mode: str) -> SpatialSessionState:
        return self.session.set_mode(mode)

    def next_event(self) -> SpatialGestureEvent:
        state = self.session.snapshot()
        if not state.enabled:
            return self.idle_event(state)

        frame = self.camera.read_frame()
        if frame is None:
            self.session.record_error("No frame available from webcam.")
            return self.idle_event(state, confidence=0.0)

        try:
            hands = self.tracker.detect(frame)
        except SpatialError as exc:
            self.session.record_error(str(exc))
            return self.idle_event(state, confidence=0.0)

        if not hands:
            self.session.record_gesture(GESTURE_IDLE)
            return self.idle_event(state, confidence=0.0)

        primary = hands[0]
        points = primary["points"]
        gesture, confidence, fingers = self.gestures.classify(points)
        position = self.mapper.palm_position(points)
        self.session.record_gesture(gesture)
        self.session.record_error(None)
        return SpatialGestureEvent(
            session_id=state.session_id,
            mode=state.mode,
            gesture=gesture,
            hand=primary["hand"],
            confidence=max(confidence, float(primary.get("hand_confidence") or 0.0) * 0.5),
            position=position,
            fingers=fingers,
            timestamp=int(time.time()),
        )

    def idle_event(self, state: SpatialSessionState | None = None, *, confidence: float = 0.0) -> SpatialGestureEvent:
        state = state or self.session.snapshot()
        return SpatialGestureEvent(
            session_id=state.session_id,
            mode=state.mode,
            gesture=GESTURE_IDLE,
            hand="unknown",
            confidence=confidence,
            position=SpatialPosition(x=0.5, y=0.5, z=0.0),
            fingers=FingerState(),
            timestamp=int(time.time()),
        )


_SPATIAL_SERVICE = SpatialService()


def get_spatial_service() -> SpatialService:
    return _SPATIAL_SERVICE
