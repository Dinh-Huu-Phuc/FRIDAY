"""On-demand, local-only understanding of the user's current screen."""

from __future__ import annotations

import asyncio
import base64
import concurrent.futures
import json
import logging
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from friday.app.computer.capture_effect import screen_capture_animation
from friday.app.computer.router.routes import observe_computer
from friday.app.computer.schemas.requests import ObserveRequest
from friday.core.db.services import ScreenshotArchiveService, screenshot_cloud_enabled


logger = logging.getLogger(__name__)
_ARCHIVE_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="friday-screenshot-archive",
)


_SCREEN_QUESTION_PATTERNS = (
    r"\bwhat (?:am i|are we) looking at\b",
    r"\bwhat (?:is|is there|do you see)(?: currently)? on (?:my|the|this) screen\b",
    r"\bwhat do you see (?:on|in) (?:my|the|this) screen\b",
    r"\b(?:describe|analy[sz]e|understand|read|inspect) (?:my|the|this) screen\b",
    r"\bcan you see (?:my|the|this) screen\b",
    r"\bdo you know what i(?:'m| am) (?:looking at|viewing)\b",
    r"\bwhat (?:is|do you see)(?: displayed)? (?:on|across) all (?:my )?screens\b",
    r"\b(?:describe|inspect|analy[sz]e) (?:all (?:of )?(?:my )?|every )(?:screens?|monitors?)\b",
)

_ALL_SCREEN_PATTERNS = (
    r"\ball (?:of )?(?:my|the) (?:screens|monitors)\b",
    r"\bevery (?:screen|monitor)\b",
    r"\bacross (?:all|my|the) (?:screens|monitors)\b",
    r"\b(?:all|both) monitors\b",
)


def is_screen_understanding_request(message: str) -> bool:
    """Return whether a user explicitly asked FRIDAY to inspect the screen."""
    normalized = " ".join(message.lower().strip().split())
    return any(re.search(pattern, normalized) for pattern in _SCREEN_QUESTION_PATTERNS)


def wants_all_screens(message: str) -> bool:
    normalized = " ".join(message.lower().strip().split())
    return any(re.search(pattern, normalized) for pattern in _ALL_SCREEN_PATTERNS)


def _ollama_endpoint() -> str:
    base_url = os.getenv("FRIDAY_VISION_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    if base_url not in {"http://127.0.0.1:11434", "http://localhost:11434"}:
        raise ValueError("FRIDAY_VISION_BASE_URL must point to the local Ollama server")
    return f"{base_url}/api/chat"


def _observe_current_screen(question: str):
    with screen_capture_animation():
        return observe_computer(
            ObserveRequest(
                goal=question,
                compress_image=True,
                capture_scope="all" if wants_all_screens(question) else "active",
            )
        ).observation


def _analyze_screen_sync(question: str) -> str:
    observation = _observe_current_screen(question)
    screen_images = observation.screen_images or []
    if screen_images:
        image_paths = [
            Path(
                image.compressed_screenshot_path or image.screenshot_path
            ).resolve()
            for image in screen_images
        ]
        image_labels = "; ".join(
            f"Image {position} is Monitor {image.monitor_index}"
            f"{' (active)' if image.is_active else ''}, {image.width}x{image.height}"
            for position, image in enumerate(screen_images, start=1)
        )
    else:
        image_paths = [
            Path(
                observation.compressed_screenshot_path
                or observation.screenshot_path
            ).resolve()
        ]
        image_labels = "Image 1 is the active screen"

    image_data = [
        base64.b64encode(image_path.read_bytes()).decode("ascii")
        for image_path in image_paths
    ]
    _queue_cloud_archive(observation, question)
    _remove_raw_screen_images(observation)
    active_window = observation.active_window_title.strip() or "unknown"
    prompt = (
        "Answer the user's question concisely in English using only visible evidence in "
        "the supplied screen image or images. Use the active monitor unless the user asks "
        "about every screen. Describe the main application or page and prominent objects. "
        "Do not identify people, repeat secrets, or invent unreadable details. State any "
        f"uncertainty. {image_labels}. Active window: {active_window}. "
        f"User question: {question}"
    )
    payload = json.dumps(
        {
            "model": os.getenv("FRIDAY_VISION_MODEL", "gemma3:4b"),
            "stream": False,
            "messages": [
                {"role": "user", "content": prompt, "images": image_data},
            ],
        }
    ).encode("utf-8")
    request = Request(
        _ollama_endpoint(),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))
    answer = str(result.get("message", {}).get("content", "")).strip()
    return answer or "I captured the screen, but the local vision model returned no description."


def _remove_raw_screen_images(observation) -> None:
    images = observation.screen_images or []
    raw_paths = (
        [Path(image.screenshot_path) for image in images]
        if images
        else [Path(observation.screenshot_path)]
    )
    for raw_path in raw_paths:
        try:
            raw_path.resolve().unlink(missing_ok=True)
        except OSError:
            continue


def _queue_cloud_archive(observation, question: str) -> None:
    if not screenshot_cloud_enabled():
        return

    def archive() -> None:
        try:
            result = ScreenshotArchiveService().archive(
                observation,
                user_question=question,
            )
            if not result.ok:
                logger.warning("Screenshot cloud archive skipped: %s", result.message)
        except Exception:
            logger.exception("Unexpected screenshot cloud archive failure")

    _ARCHIVE_EXECUTOR.submit(archive)


async def understand_current_screen(question: str) -> str:
    """Capture and inspect the current screen using only a local vision server."""
    try:
        return await asyncio.to_thread(_analyze_screen_sync, question)
    except (ConnectionError, HTTPError, URLError):
        model = os.getenv("FRIDAY_VISION_MODEL", "gemma3:4b")
        return (
            "Local screen vision is not available yet. Start Ollama and install the model "
            f"configured by FRIDAY_VISION_MODEL (currently {model})."
        )
    except Exception as exc:
        return f"I could not analyze the current screen ({type(exc).__name__})."
