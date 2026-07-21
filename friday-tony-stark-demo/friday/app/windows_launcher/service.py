"""Shared service for searching and opening local Windows apps."""

from __future__ import annotations

import os
import subprocess

from friday.app.windows_launcher.matcher import rank_apps
from friday.app.windows_launcher.registry import discover_apps, is_windows
from friday.app.windows_launcher.schemas import AppLaunchResponse, AppMatch, AppSearchResponse


def search_apps(query: str, limit: int = 8) -> AppSearchResponse:
    if not is_windows():
        return AppSearchResponse(
            ok=False,
            query=query,
            items=[],
            message="Windows app launcher is only available on Windows.",
        )

    items = rank_apps(query=query, apps=list(discover_apps()), limit=limit)
    message = f"Found {len(items)} matching app(s)." if items else "No matching apps found."
    return AppSearchResponse(query=query, items=items, message=message)


def open_app(
    query: str | None = None,
    app_id: str | None = None,
    path: str | None = None,
    min_score: float = 0.55,
) -> AppLaunchResponse:
    if not is_windows():
        return AppLaunchResponse(ok=False, message="Windows app launcher is only available on Windows.")

    selected = _select_app(query=query, app_id=app_id, path=path, min_score=min_score)
    if isinstance(selected, AppLaunchResponse):
        return selected

    try:
        _launch_selected(selected)
    except OSError as exc:
        return AppLaunchResponse(
            ok=False,
            message=f"Failed to launch {selected.name}: {exc}",
            selected=selected,
        )

    return AppLaunchResponse(ok=True, message=f"Launched {selected.name}.", selected=selected)


def _select_app(
    query: str | None,
    app_id: str | None,
    path: str | None,
    min_score: float,
) -> AppMatch | AppLaunchResponse:
    if path:
        return AppMatch(name=os.path.splitext(os.path.basename(path))[0], path=path, source="direct_path", score=1.0)
    if app_id:
        match = _find_by_app_id(app_id)
        return match or AppMatch(name=app_id, app_id=app_id, source="direct_app_id", score=1.0)
    if not query or not query.strip():
        return AppLaunchResponse(ok=False, message="Provide query, app_id, or path to launch an app.")

    candidates = search_apps(query, limit=5).items
    if not candidates:
        return AppLaunchResponse(ok=False, message="No matching apps found.", candidates=[])

    selected = candidates[0]
    if selected.score < min_score:
        return AppLaunchResponse(
            ok=False,
            message="Best match is below the confidence threshold.",
            candidates=candidates,
        )
    return selected


def _find_by_app_id(app_id: str) -> AppMatch | None:
    for app in discover_apps():
        if app.app_id == app_id:
            return app.model_copy(update={"score": 1.0})
    return None


def _launch_selected(app: AppMatch) -> None:
    if app.path:
        os.startfile(app.path)  # type: ignore[attr-defined]
        return
    if app.app_id:
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                'param($AppId) Start-Process ("shell:AppsFolder\\" + $AppId)',
                app.app_id,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    raise OSError("Selected app has no launchable path or AppID.")
