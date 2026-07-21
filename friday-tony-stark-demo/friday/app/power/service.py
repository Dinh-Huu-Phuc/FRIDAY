"""File-backed runtime power state shared by FastAPI and LiveKit."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from friday.app.agent_console.greeting_engine import build_time_greeting
from friday.app.power.activity import record_power_activity
from friday.app.power.intents import PowerIntent, match_power_intent
from friday.app.power.name.responses import select_power_response


PowerState = Literal["active", "sleeping"]
_LOCK = threading.RLock()
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_STATE_PATH = _PROJECT_ROOT / "friday" / "log" / "runtime" / "power_state.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _initial_state() -> PowerState:
    return "sleeping" if os.getenv("FRIDAY_INITIAL_STATE", "active").lower() == "sleeping" else "active"


def _state_path() -> Path:
    configured = os.getenv("FRIDAY_POWER_STATE_PATH", "").strip()
    return Path(configured).expanduser().resolve() if configured else _DEFAULT_STATE_PATH


@dataclass(frozen=True, slots=True)
class PowerSnapshot:
    state: PowerState
    changed_at: str
    source: str

    @property
    def sleeping(self) -> bool:
        return self.state == "sleeping"

    def to_dict(self) -> dict[str, str | bool]:
        return {**asdict(self), "sleeping": self.sleeping}


@dataclass(frozen=True, slots=True)
class PowerCommandResult:
    handled: bool
    reply: str
    snapshot: PowerSnapshot


def _write_snapshot(snapshot: PowerSnapshot) -> PowerSnapshot:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
    temporary.replace(path)
    return snapshot


def initialize_power_state(*, source: str = "startup") -> PowerSnapshot:
    with _LOCK:
        return _write_snapshot(PowerSnapshot(_initial_state(), _now_iso(), source))


def get_power_state() -> PowerSnapshot:
    with _LOCK:
        path = _state_path()
        if not path.is_file():
            return initialize_power_state(source="implicit_startup")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            state: PowerState = "sleeping" if payload.get("state") == "sleeping" else "active"
            return PowerSnapshot(
                state=state,
                changed_at=str(payload.get("changed_at") or _now_iso()),
                source=str(payload.get("source") or "unknown"),
            )
        except (OSError, ValueError, TypeError):
            return initialize_power_state(source="state_recovery")


def set_power_state(state: PowerState, *, source: str) -> PowerSnapshot:
    with _LOCK:
        current = get_power_state()
        if current.state == state:
            return current
        return _write_snapshot(PowerSnapshot(state, _now_iso(), source))


def handle_power_message(
    message: str,
    *,
    source: str,
    silent_when_sleeping: bool = False,
) -> PowerCommandResult:
    match = match_power_intent(message)
    intent = match.intent
    current = get_power_state()

    if intent == PowerIntent.SLEEP:
        if current.sleeping:
            reply = select_power_response("already_sleeping")
            return PowerCommandResult(True, reply, current)
        snapshot = set_power_state("sleeping", source=source)
        reply = select_power_response(match.response_group)
        return PowerCommandResult(True, reply, snapshot)

    if intent == PowerIntent.WAKE:
        if not current.sleeping:
            record_power_activity(source=source)
            reply_group = (
                match.response_group
                if match.response_group not in {"wake_time", ""}
                else "already_awake"
            )
            return PowerCommandResult(True, select_power_response(reply_group), current)
        snapshot = set_power_state("active", source=source)
        record_power_activity(source=source)
        reply = (
            build_time_greeting(event="wake")
            if match.response_group == "wake_time"
            else select_power_response(match.response_group)
        )
        return PowerCommandResult(True, reply, snapshot)

    if current.sleeping:
        if silent_when_sleeping:
            return PowerCommandResult(True, "", current)
        return PowerCommandResult(True, "FRIDAY is sleeping. Say FRIDAY wake up to continue.", current)

    if message.strip():
        record_power_activity(source=source)
    return PowerCommandResult(False, "", current)
