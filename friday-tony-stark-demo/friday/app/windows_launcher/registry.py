"""Read-only discovery of locally installed Windows apps."""

from __future__ import annotations

import json
import os
import platform
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from friday.app.windows_launcher.schemas import AppMatch


def is_windows() -> bool:
    return platform.system().lower() == "windows"


@lru_cache(maxsize=1)
def discover_apps() -> tuple[AppMatch, ...]:
    """Return apps from Start Menu shortcuts and Windows Start app IDs."""
    if not is_windows():
        return tuple()

    apps: list[AppMatch] = []
    apps.extend(_discover_start_menu_shortcuts())
    apps.extend(_discover_start_apps())
    return tuple(_dedupe_apps(apps))


def _discover_start_menu_shortcuts() -> list[AppMatch]:
    roots = [
        _join_env_path("APPDATA", "Microsoft", "Windows", "Start Menu", "Programs"),
        _join_env_path("ProgramData", "Microsoft", "Windows", "Start Menu", "Programs"),
    ]
    apps: list[AppMatch] = []

    for root in roots:
        if not root or not root.exists():
            continue
        for shortcut in root.rglob("*.lnk"):
            apps.append(
                AppMatch(
                    name=shortcut.stem,
                    path=str(shortcut),
                    source="start_menu",
                )
            )
    return apps


def _discover_start_apps() -> list[AppMatch]:
    script = "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Depth 3"
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    stdout = completed.stdout or ""
    if completed.returncode != 0 or not stdout.strip():
        return []

    try:
        raw = json.loads(stdout)
    except json.JSONDecodeError:
        return []

    records: list[dict[str, Any]]
    if isinstance(raw, list):
        records = [item for item in raw if isinstance(item, dict)]
    elif isinstance(raw, dict):
        records = [raw]
    else:
        records = []

    apps: list[AppMatch] = []
    for item in records:
        name = str(item.get("Name") or "").strip()
        app_id = str(item.get("AppID") or "").strip()
        if not name or not app_id:
            continue
        apps.append(AppMatch(name=name, app_id=app_id, source="start_apps"))
    return apps


def _join_env_path(env_name: str, *parts: str) -> Path | None:
    root = os.environ.get(env_name)
    if not root:
        return None
    return Path(root, *parts)


def _dedupe_apps(apps: list[AppMatch]) -> list[AppMatch]:
    seen: set[tuple[str, str | None, str | None]] = set()
    unique: list[AppMatch] = []

    for app in apps:
        key = (app.name.casefold(), app.app_id, app.path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(app)
    return unique
