from __future__ import annotations

import asyncio
import mimetypes
import os
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from friday.app.agent_console.schemas import ConsoleChatRequest
from friday.app.agent_console.service import get_agent_console_service
from friday.app.agent_console.greeting_engine import build_time_greeting
from friday.app.power import PowerIntent, detect_power_intent, get_power_state
from friday.app.research import SEARCH_ACKNOWLEDGEMENT, should_announce_search
from friday.core.db import (
    CredentialAlreadyConfiguredError,
    InvalidPasswordError,
    PasswordConfirmationError,
    get_core_access_gate,
)
from friday.src.services.agent.service import build_startup_briefing, chat, greeting


STATIC_DIR = Path(__file__).resolve().parent / "static"
FAVICON_PATH = Path(__file__).resolve().parents[2] / "assets" / "img" / "favicon.ico"
CORE_VIDEO_PATH = Path(__file__).resolve().parents[2] / "assets" / "videos" / "FRIDAY.mp4"
CLONE_ICON_PATH = (
    Path(__file__).resolve().parents[2]
    / "assets"
    / "icons"
    / "fontawesome"
    / "clone-regular-full.svg"
)
UI_SESSION_ID = "python-ui"
MAX_CHAT_MESSAGE_LENGTH = 8_000
CORE_SESSION_COOKIE = "friday_core_session"

router = APIRouter(tags=["web-ui"])


class CoreSetupRequest(BaseModel):
    password: str
    confirmation: str


class CoreUnlockRequest(BaseModel):
    password: str


def _request_is_unlocked(request: Request) -> bool:
    return get_core_access_gate().is_unlocked(
        request.cookies.get(CORE_SESSION_COOKIE)
    )


def _require_unlocked(request: Request) -> None:
    if not _request_is_unlocked(request):
        raise HTTPException(status_code=401, detail="FRIDAY core is locked.")


def _unlocked_response(token: str, *, secure: bool) -> JSONResponse:
    response = JSONResponse({"ok": True, "next": "/ui"})
    response.set_cookie(
        key=CORE_SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=secure,
        samesite="strict",
        path="/",
    )
    return response


def _fast_startup_enabled() -> bool:
    return os.getenv("FRIDAY_START_MODE", "fast").strip().lower() == "fast"


async def _send_background_briefing(websocket: WebSocket, service) -> None:
    briefing = await build_startup_briefing()
    if get_power_state().sleeping:
        return
    snapshot = service.add_assistant_message(session_id=UI_SESSION_ID, content=briefing)
    await websocket.send_json({"type": "snapshot", "payload": snapshot})


def mount_web_ui_static(app: FastAPI) -> None:
    mimetypes.add_type("font/woff2", ".woff2")
    # Keep native Python modules under static/desktop_ui out of the HTTP surface.
    for directory in ("Core_UI", "Unlock", "vendor"):
        app.mount(
            f"/ui/static/{directory}",
            StaticFiles(directory=STATIC_DIR / directory),
            name=f"friday-ui-{directory.lower()}",
        )


@router.get("/ui/unlock", include_in_schema=False)
async def friday_unlock_ui() -> FileResponse:
    return FileResponse(STATIC_DIR / "Unlock" / "unlock.html", media_type="text/html")


@router.get("/ui/access/status", include_in_schema=False)
async def core_access_status(request: Request) -> dict[str, bool]:
    gate = get_core_access_gate()
    return {
        "configured": gate.is_configured(),
        "unlocked": gate.is_unlocked(request.cookies.get(CORE_SESSION_COOKIE)),
    }


@router.post("/ui/access/setup", include_in_schema=False)
async def setup_core_access(
    payload: CoreSetupRequest,
    request: Request,
) -> JSONResponse:
    try:
        token = get_core_access_gate().setup(
            payload.password,
            payload.confirmation,
        )
    except (InvalidPasswordError, PasswordConfirmationError) as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)
    except CredentialAlreadyConfiguredError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=409)
    return _unlocked_response(token, secure=request.url.scheme == "https")


@router.post("/ui/access/unlock", include_in_schema=False)
async def unlock_core_access(
    payload: CoreUnlockRequest,
    request: Request,
) -> JSONResponse:
    gate = get_core_access_gate()
    if not gate.is_configured():
        return JSONResponse(
            {"detail": "Create the FRIDAY core password first."},
            status_code=409,
        )
    try:
        token = gate.unlock(payload.password)
    except InvalidPasswordError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=401)
    return _unlocked_response(token, secure=request.url.scheme == "https")


@router.get("/ui", response_class=HTMLResponse)
async def friday_ui(request: Request) -> Response:
    if not _request_is_unlocked(request):
        return RedirectResponse(url="/ui/unlock", status_code=303)
    return HTMLResponse("""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>FRIDAY Local Core</title>
    <link rel="icon" href="/favicon.ico" sizes="any" />
    <link rel="stylesheet" href="/ui/static/vendor/katex/katex.min.css?v=0.17.0" />
    <link rel="stylesheet" href="/ui/static/Core_UI/styles.css?v=20260721-wake" />
  </head>
  <body>
    <main class="app-shell" data-core-state="disconnected">
      <section class="history-dock" id="history-dock" aria-label="Conversation history">
        <div class="history-head">
          <span>Conversation</span>
          <div class="history-actions">
            <button id="toggle-history" class="icon-button" type="button" aria-label="Hide history">Hide</button>
            <button id="clear-chat" class="icon-button" type="button" aria-label="Clear chat">Clear</button>
          </div>
        </div>
        <div id="messages" class="conversation-stack" aria-live="polite"></div>
      </section>

      <button id="connection-indicator" class="connection-indicator" type="button" aria-label="Connection details">
        <span class="connection-dot"></span>
        <span id="transport">offline</span>
      </button>
      <section id="connection-popover" class="connection-popover" hidden>
        <dl>
          <div><dt>Core service</dt><dd id="core-service-status">checking</dd></div>
          <div><dt>WebSocket</dt><dd id="websocket-status">offline</dd></div>
          <div><dt>Voice</dt><dd id="voice-status">waiting</dd></div>
        </dl>
      </section>

      <section class="core-stage" aria-label="FRIDAY AI core">
        <div id="core-video-layer" class="core-video-layer" aria-hidden="true">
          <video
            id="core-video"
            data-src="/ui/media/core-video?v=20260717"
            autoplay
            muted
            loop
            playsinline
            preload="auto"
          ></video>
          <span class="core-video-shade"></span>
          <span id="core-video-message" class="core-video-message">Loading FRIDAY visual...</span>
        </div>
        <div id="core-orb" class="core-orb" aria-hidden="true">
          <span class="orb-shell"></span>
          <span class="orb-glass"></span>
          <span class="orb-core"></span>
          <span class="orb-wave orb-wave-a"></span>
          <span class="orb-wave orb-wave-b"></span>
          <span class="orb-reflection"></span>
        </div>
        <time id="sleep-clock" class="sleep-clock" aria-live="off">
          <span id="sleep-time" class="sleep-time">00:00</span>
          <span id="sleep-date" class="sleep-date">Monday, January 1</span>
        </time>
        <p class="core-kicker">FRIDAY LOCAL CORE</p>
        <p id="status" class="core-status">Connecting to local core...</p>
      </section>

      <form id="chat-form" class="prompt-input" aria-label="Prompt FRIDAY">
        <button id="mic-button" class="prompt-action" type="button" aria-label="Start voice input">Mic</button>
        <canvas id="mic-waveform" class="mic-waveform" width="150" height="36" aria-label="Live microphone level"></canvas>
        <textarea id="message-input" rows="1" autocomplete="off" placeholder="Talk or type to FRIDAY..."></textarea>
        <button class="prompt-send" type="submit">Send</button>
      </form>

      <button id="settings-toggle" class="settings-toggle" type="button" aria-label="Open settings">Settings</button>
      <aside id="settings-panel" class="settings-panel" hidden>
        <div class="settings-head">
          <span>Core Appearance</span>
          <button id="settings-close" class="icon-button" type="button">Close</button>
        </div>
        <fieldset class="visual-picker">
          <legend>Interface</legend>
          <div class="segmented-control">
            <label>
              <input type="radio" name="core-visual" value="orb" />
              <span>Core Orb</span>
            </label>
            <label>
              <input type="radio" name="core-visual" value="video" />
              <span>FRIDAY Video</span>
            </label>
          </div>
        </fieldset>
        <section class="runtime-setting" aria-labelledby="auto-sleep-title">
          <div class="runtime-setting-head">
            <span id="auto-sleep-title">Automatic sleep</span>
            <output id="auto-sleep-status">Loading...</output>
          </div>
          <div class="auto-sleep-control">
            <label for="auto-sleep-minutes">Idle time</label>
            <div class="number-action">
              <input id="auto-sleep-minutes" type="number" min="1" max="1440" step="1" inputmode="numeric" />
              <span>min</span>
              <button id="apply-auto-sleep" class="settings-apply" type="button">Apply</button>
            </div>
          </div>
          <p id="auto-sleep-feedback" class="settings-feedback" aria-live="polite"></p>
        </section>
        <label>Primary RGB color <input id="primary-color" type="color" /></label>
        <label>Secondary RGB color <input id="secondary-color" type="color" /></label>
        <label>Glow intensity <input id="glow-intensity" type="range" min="0.4" max="1.8" step="0.05" /></label>
        <label>Pulse speed <input id="pulse-speed" type="range" min="0.6" max="2.4" step="0.05" /></label>
        <label>Orb size <input id="orb-size" type="range" min="180" max="360" step="4" /></label>
        <label class="switch-row"><input id="voice-reactive" type="checkbox" /> Voice reactive effect</label>
        <label class="switch-row"><input id="reduce-motion" type="checkbox" /> Reduce motion</label>
        <label class="switch-row"><input id="voice-enabled" type="checkbox" /> Voice reply</label>
      </aside>
    </main>
    <script src="/ui/static/vendor/katex/katex.min.js?v=0.17.0"></script>
    <script src="/ui/static/vendor/katex/contrib/auto-render.min.js?v=0.17.0"></script>
    <script src="/ui/static/Core_UI/app.js?v=20260721-wake"></script>
  </body>
</html>
""")


@router.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(FAVICON_PATH, media_type="image/x-icon")


@router.get("/ui/assets/icons/clone.svg", include_in_schema=False)
async def conversation_clone_icon() -> FileResponse:
    return FileResponse(CLONE_ICON_PATH, media_type="image/svg+xml")


@router.get("/ui/media/core-video", include_in_schema=False)
async def core_interface_video(request: Request) -> FileResponse:
    _require_unlocked(request)
    if not CORE_VIDEO_PATH.is_file():
        raise HTTPException(status_code=404, detail="FRIDAY core video is unavailable.")
    return FileResponse(CORE_VIDEO_PATH, media_type="video/mp4")


@router.websocket("/ws/chat")
async def chat_socket(websocket: WebSocket) -> None:
    if not get_core_access_gate().is_unlocked(
        websocket.cookies.get(CORE_SESSION_COOKIE)
    ):
        await websocket.close(code=4401, reason="FRIDAY core is locked")
        return
    await websocket.accept()
    service = get_agent_console_service()
    snapshot = service.get_snapshot(session_id=UI_SESSION_ID)
    await websocket.send_json({
        "type": "snapshot",
        "payload": snapshot,
    })
    await websocket.send_json({"type": "power", "payload": get_power_state().to_dict()})

    messages = snapshot.get("messages") or []
    briefing_task: asyncio.Task | None = None
    if len(messages) <= 1 and not get_power_state().sleeping:
        await websocket.send_json({"type": "state", "state": "briefing"})
        if _fast_startup_enabled():
            snapshot = service.add_assistant_message(
                session_id=UI_SESSION_ID,
                content=(
                    f"{build_time_greeting(event='startup')} "
                    "Live information is warming up in the background."
                ),
            )
            await websocket.send_json({"type": "snapshot", "payload": snapshot})
            briefing_task = asyncio.create_task(_send_background_briefing(websocket, service))
        else:
            await _send_background_briefing(websocket, service)

    try:
        while True:
            payload = await websocket.receive_json()
            packet_type = str(payload.get("type", "chat")).strip() or "chat"
            message = str(payload.get("message", "")).strip()
            channel = str(payload.get("channel", "text")).strip() or "text"
            if packet_type == "clear":
                response = service.archive_and_reset_chat(
                    session_id=UI_SESSION_ID,
                    reason="manual_clear",
                )
                await websocket.send_json({"type": "cleared", "payload": response})
                continue

            if not message:
                await websocket.send_json({"type": "error", "message": "Message must not be empty."})
                continue
            if len(message) > MAX_CHAT_MESSAGE_LENGTH:
                await websocket.send_json({"type": "error", "message": "Message is too long."})
                continue

            if (
                channel == "voice"
                and get_power_state().sleeping
                and detect_power_intent(message) != PowerIntent.WAKE
            ):
                await websocket.send_json({"type": "power", "payload": get_power_state().to_dict()})
                await websocket.send_json({"type": "voice_ignored", "message": message})
                continue

            if should_announce_search(message):
                await websocket.send_json(
                    {
                        "type": "search_acknowledgement",
                        "message": SEARCH_ACKNOWLEDGEMENT,
                    }
                )
                await websocket.send_json({"type": "state", "state": "searching"})
            else:
                await websocket.send_json({"type": "state", "state": "thinking"})
            response = await chat(
                ConsoleChatRequest(
                    message=message,
                    channel="voice" if channel == "voice" else "text",
                    session_id=UI_SESSION_ID,
                )
            )
            await websocket.send_json({"type": "snapshot", "payload": response})
            await websocket.send_json({"type": "power", "payload": get_power_state().to_dict()})
    except WebSocketDisconnect:
        return
    finally:
        if briefing_task and not briefing_task.done():
            briefing_task.cancel()


@router.get("/ui/greeting")
async def ui_greeting(request: Request) -> dict:
    _require_unlocked(request)
    return await greeting()


@router.post("/ui/chat/clear")
async def clear_ui_chat(request: Request) -> dict:
    _require_unlocked(request)
    return get_agent_console_service().archive_and_reset_chat(
        session_id=UI_SESSION_ID,
        reason="ui_closed",
    )
