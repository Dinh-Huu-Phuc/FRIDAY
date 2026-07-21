from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from urllib.request import Request, urlopen

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from friday.src.config.settings import get_settings
from friday.src.common.local_access import LocalAccessMiddleware
from friday.src.router.api_router import api_router
from friday.src.sse.routes import router as sse_router
from friday.src.UI.routes import router as web_ui_router, mount_web_ui_static
from friday.app.agent_console.service import get_agent_console_service
from friday.app.power import (
    AutoSleepMonitor,
    initialize_power_state,
    restore_application_windows,
)


def create_app() -> FastAPI:
    settings = get_settings()
    if os.getenv("FRIDAY_WINDOW_RESTORE_ON_STARTUP", "true").lower() in {"1", "true", "yes", "on"}:
        restore_application_windows()
    initialize_power_state(source="fastapi_startup")
    auto_sleep_monitor = AutoSleepMonitor()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if settings.expose_api_docs else None,
        redoc_url="/redoc" if settings.expose_api_docs else None,
        openapi_url="/openapi.json" if settings.expose_api_docs else None,
    )

    app.add_middleware(LocalAccessMiddleware, enabled=settings.local_only)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    app.include_router(sse_router, prefix=settings.sse_prefix, tags=["sse"])
    mount_web_ui_static(app)
    app.include_router(web_ui_router)

    @app.on_event("shutdown")
    def archive_ui_chat_on_shutdown() -> None:
        auto_sleep_monitor.stop()
        get_agent_console_service().archive_and_reset_chat(
            session_id="python-ui",
            reason="server_shutdown",
        )

    @app.on_event("startup")
    async def warm_background_services() -> None:
        auto_sleep_monitor.start()
        if os.getenv("FRIDAY_BACKGROUND_WARMUP", "true").lower() not in {"1", "true", "yes", "on"}:
            return
        if os.getenv("FRIDAY_OLLAMA_PRELOAD", "true").lower() in {"1", "true", "yes", "on"}:
            asyncio.create_task(asyncio.to_thread(_preload_ollama_model))

    @app.get("/", include_in_schema=False)
    def root_redirect() -> RedirectResponse:
        return RedirectResponse(url="/ui")

    return app


def _preload_ollama_model() -> None:
    base_url = os.getenv("FRIDAY_VISION_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    if base_url not in {"http://127.0.0.1:11434", "http://localhost:11434"}:
        return
    payload = json.dumps({
        "model": os.getenv("FRIDAY_VISION_MODEL", "gemma3:4b"),
        "prompt": "",
        "stream": False,
        "keep_alive": "10m",
    }).encode("utf-8")
    request = Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            response.read(1)
    except Exception:
        return


app = create_app()


def _find_chrome(configured_path: str = "") -> Path | None:
    candidates = [configured_path] if configured_path else []
    for executable in ("chrome.exe", "chrome", "google-chrome", "google-chrome-stable"):
        discovered = shutil.which(executable)
        if discovered:
            candidates.append(discovered)

    for env_name, relative_path in (
        ("LOCALAPPDATA", "Google/Chrome/Application/chrome.exe"),
        ("PROGRAMFILES", "Google/Chrome/Application/chrome.exe"),
        ("PROGRAMFILES(X86)", "Google/Chrome/Application/chrome.exe"),
    ):
        root = os.getenv(env_name)
        if root:
            candidates.append(str(Path(root) / relative_path))

    candidates.extend(
        [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
        ]
    )
    return next((Path(candidate) for candidate in candidates if candidate and Path(candidate).is_file()), None)


def _open_ui_in_browser(url: str, configured_path: str = "") -> None:
    chrome = _find_chrome(configured_path)
    if chrome:
        try:
            subprocess.Popen(
                [str(chrome), url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        except OSError:
            pass
    webbrowser.open_new_tab(url)


def _open_ui_when_ready(server: uvicorn.Server, url: str, configured_path: str = "") -> None:
    while not server.started and not server.should_exit:
        time.sleep(0.05)
    if server.started and not server.should_exit:
        _open_ui_in_browser(url, configured_path)


def main() -> None:
    settings = get_settings()
    config = uvicorn.Config(
        "friday.src.main:app",
        host=settings.host,
        port=settings.port,
        http="h11",
        reload=False,
        server_header=False,
    )
    server = uvicorn.Server(config)

    if settings.desktop_ui_enabled:
        server_thread = threading.Thread(
            target=server.run,
            name="friday-api-server",
            daemon=True,
        )
        server_thread.start()
        while not server.started and server_thread.is_alive():
            time.sleep(0.05)
        if not server.started:
            raise RuntimeError("FRIDAY API failed to start before the desktop UI.")

        logging_rules = os.getenv("QT_LOGGING_RULES", "").strip()
        ffmpeg_rule = "qt.multimedia.ffmpeg=false"
        if ffmpeg_rule not in logging_rules:
            os.environ["QT_LOGGING_RULES"] = ";".join(
                rule for rule in (logging_rules, ffmpeg_rule) if rule
            )

        from friday.src.UI.static.desktop_ui.app import run_desktop_app

        try:
            run_desktop_app()
        finally:
            server.should_exit = True
            server_thread.join(timeout=10)
        return

    if settings.auto_open_browser:
        browser_thread = threading.Thread(
            target=_open_ui_when_ready,
            args=(server, f"http://127.0.0.1:{settings.port}/ui", settings.browser_path),
            name="friday-ui-launcher",
            daemon=True,
        )
        browser_thread.start()

    server.run()


if __name__ == "__main__":
    main()
