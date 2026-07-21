"""Lifecycle controller for the short-lived native capture overlay."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from uuid import uuid4


_FRIDAY_DIR = Path(__file__).resolve().parents[3]
_PROJECT_ROOT = _FRIDAY_DIR.parent
_RUNTIME_DIR = _FRIDAY_DIR / "log" / "runtime"
_CAPTURE_EFFECT_LOCK = threading.RLock()


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


class CaptureEffectSession:
    """Start one overlay process and guarantee that it is reaped afterward."""

    def __init__(self, *, duration_ms: int | None = None) -> None:
        self.duration_ms = duration_ms or _env_int(
            "FRIDAY_CAPTURE_EFFECT_DURATION_MS", 1100, 450, 3000
        )
        self.state_path = _RUNTIME_DIR / f"capture_effect_{uuid4().hex}.json"
        self.process: subprocess.Popen[bytes] | None = None

    def start(self) -> bool:
        if os.name != "nt" or not _env_flag("FRIDAY_CAPTURE_EFFECT_ENABLED", True):
            return False

        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
        try:
            self.process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "friday.app.computer.capture_effect.overlay",
                    "--state-path",
                    str(self.state_path),
                    "--duration-ms",
                    str(self.duration_ms),
                ],
                cwd=_PROJECT_ROOT,
                env={**os.environ, "FRIDAY_CAPTURE_EFFECT_CHILD": "1"},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
        except OSError:
            self.process = None
            return False

        deadline = time.monotonic() + _env_int(
            "FRIDAY_CAPTURE_EFFECT_STARTUP_TIMEOUT_MS", 1800, 300, 5000
        ) / 1000.0
        while time.monotonic() < deadline:
            state = self._read_state()
            # A Windows venv launcher can keep a different PID from its Python child.
            # The state path is unique per session, so readiness is sufficient here.
            if state.get("ready"):
                return True
            if self.process.poll() is not None:
                break
            time.sleep(0.02)

        self.finish()
        return False

    def finish(self) -> None:
        process = self.process
        self.process = None
        if process is not None and process.poll() is None:
            try:
                process.wait(timeout=(self.duration_ms / 1000.0) + 0.8)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1.0)
        self.state_path.unlink(missing_ok=True)

    def _read_state(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            return {}


@contextmanager
def screen_capture_animation() -> Iterator[bool]:
    """Show the capture overlay without ever blocking the screenshot fallback."""
    with _CAPTURE_EFFECT_LOCK:
        session = CaptureEffectSession()
        started = session.start()
        try:
            yield started
        finally:
            session.finish()
