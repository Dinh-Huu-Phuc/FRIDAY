"""File-backed user activity shared by FRIDAY runtime processes."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


_LOCK = threading.RLock()
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_ACTIVITY_PATH = (
    _PROJECT_ROOT / "friday" / "log" / "runtime" / "power_activity.json"
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _activity_path() -> Path:
    configured = os.getenv("FRIDAY_POWER_ACTIVITY_PATH", "").strip()
    return (
        Path(configured).expanduser().resolve()
        if configured
        else _DEFAULT_ACTIVITY_PATH
    )


@dataclass(frozen=True, slots=True)
class PowerActivitySnapshot:
    last_activity_at: str
    source: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def as_datetime(self) -> datetime:
        parsed = datetime.fromisoformat(self.last_activity_at)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def record_power_activity(
    *,
    source: str,
    at: datetime | None = None,
) -> PowerActivitySnapshot:
    moment = at or _utc_now()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    snapshot = PowerActivitySnapshot(
        last_activity_at=moment.astimezone(timezone.utc).isoformat(timespec="seconds"),
        source=source,
    )
    with _LOCK:
        path = _activity_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        temporary.write_text(
            json.dumps(snapshot.to_dict(), indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
    return snapshot


def get_power_activity() -> PowerActivitySnapshot:
    with _LOCK:
        path = _activity_path()
        if not path.is_file():
            return record_power_activity(source="activity_startup")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            snapshot = PowerActivitySnapshot(
                last_activity_at=str(payload["last_activity_at"]),
                source=str(payload.get("source") or "unknown"),
            )
            snapshot.as_datetime()
            return snapshot
        except (KeyError, OSError, TypeError, ValueError):
            return record_power_activity(source="activity_recovery")


def inactive_seconds(*, now: datetime | None = None) -> float:
    moment = now or _utc_now()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    elapsed = moment.astimezone(timezone.utc) - get_power_activity().as_datetime()
    return max(0.0, elapsed.total_seconds())

