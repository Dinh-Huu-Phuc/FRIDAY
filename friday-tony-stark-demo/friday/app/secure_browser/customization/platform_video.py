from __future__ import annotations

from pathlib import Path

from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineScript

PLATFORM_VIDEO_SCRIPT_NAME = "friday-platform-video-selection"
_FRIDAY_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_PATH = (
    _FRIDAY_ROOT
    / "src"
    / "UI"
    / "static"
    / "browser_ui"
    / "scripts"
    / "platform_video.js"
)


def build_platform_video_script() -> QWebEngineScript:
    script = QWebEngineScript()
    script.setName(PLATFORM_VIDEO_SCRIPT_NAME)
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
    script.setWorldId(QWebEngineScript.ScriptWorldId.ApplicationWorld)
    script.setRunsOnSubFrames(False)
    script.setSourceCode(_SCRIPT_PATH.read_text(encoding="utf-8"))
    return script


def install_platform_video_selection(profile: QWebEngineProfile) -> None:
    scripts = profile.scripts()
    if scripts.find(PLATFORM_VIDEO_SCRIPT_NAME):
        return
    scripts.insert(build_platform_video_script())
