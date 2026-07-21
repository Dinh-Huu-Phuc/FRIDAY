"""Terminal execution helpers with safety checks."""

from __future__ import annotations

import platform
import subprocess

from friday.tools.computer.safety import validate_command


def _build_shell_command(command: str) -> list[str]:
    if platform.system().lower().startswith("win"):
        return ["powershell", "-NoProfile", "-Command", command]
    return ["/bin/sh", "-lc", command]


def run_command(command: str, timeout: int = 20, safety_mode: str = "strict") -> dict[str, object]:
    safety_result = validate_command(command, safety_mode=safety_mode)
    if not safety_result.allowed:
        return {
            "ok": False,
            "command": command,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
            "safety": safety_result.to_dict(),
        }

    try:
        completed = subprocess.run(
            _build_shell_command(command),
            capture_output=True,
            text=True,
            timeout=int(timeout),
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timed_out": False,
            "safety": safety_result.to_dict(),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "command": command,
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
            "safety": safety_result.to_dict(),
        }
