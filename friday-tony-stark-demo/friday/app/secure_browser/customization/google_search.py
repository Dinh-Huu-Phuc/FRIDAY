from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineScript

GOOGLE_SEARCH_BRAND_SCRIPT_NAME = "friday-google-search-brand"
_GOOGLE_SEARCH_HOSTS = frozenset({"google.com", "www.google.com"})
_FRIDAY_ROOT = Path(__file__).resolve().parents[3]
_BROWSER_UI_ROOT = _FRIDAY_ROOT / "src" / "UI" / "static" / "browser_ui"
_SCRIPT_PATH = _BROWSER_UI_ROOT / "scripts" / "google_brand.js"
_STYLE_PATH = _BROWSER_UI_ROOT / "styles" / "google_brand.css"
_STYLE_PLACEHOLDER = "__FRIDAY_GOOGLE_BRAND_CSS__"


def is_google_search_url(value: str) -> bool:
    parsed = urlsplit(str(value or "").strip())
    return (
        parsed.scheme.lower() == "https"
        and (parsed.hostname or "").lower() in _GOOGLE_SEARCH_HOSTS
        and parsed.path.rstrip("/") == "/search"
    )


def build_google_search_brand_script() -> QWebEngineScript:
    source = _SCRIPT_PATH.read_text(encoding="utf-8")
    stylesheet = _STYLE_PATH.read_text(encoding="utf-8")
    source = source.replace(_STYLE_PLACEHOLDER, json.dumps(stylesheet))
    if _STYLE_PLACEHOLDER in source:
        raise ValueError("Google branding stylesheet placeholder was not resolved")

    script = QWebEngineScript()
    script.setName(GOOGLE_SEARCH_BRAND_SCRIPT_NAME)
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
    script.setWorldId(QWebEngineScript.ScriptWorldId.ApplicationWorld)
    script.setRunsOnSubFrames(False)
    script.setSourceCode(source)
    return script


def install_google_search_branding(profile: QWebEngineProfile) -> None:
    scripts = profile.scripts()
    if scripts.find(GOOGLE_SEARCH_BRAND_SCRIPT_NAME):
        return
    scripts.insert(build_google_search_brand_script())
