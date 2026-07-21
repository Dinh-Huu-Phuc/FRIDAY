"""Observation service for the computer module."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from friday.app.computer.config.settings import ComputerSettings
from friday.app.computer.exceptions import ComputerObservationError
from friday.app.computer.schemas.entities import ScreenImage, ScreenObservation
from friday.app.computer.schemas.requests import ObserveRequest
from friday.tools.computer import vision


class ComputerObserver:
    def __init__(self, *, settings: ComputerSettings) -> None:
        self.settings = settings

    def observe(self, request: ObserveRequest | None = None) -> ScreenObservation:
        active_request = request or ObserveRequest()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        screenshot_dir = Path(self.settings.screenshot_dir).expanduser().resolve()
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        if active_request.capture_scope in {"active", "all"}:
            return self._observe_monitors(
                active_request,
                timestamp=timestamp,
                screenshot_dir=screenshot_dir,
            )

        raw_path = screenshot_dir / f"screen_{timestamp}.png"

        try:
            capture = vision.capture_screen(raw_path)
            compressed_path: str | None = None
            if active_request.compress_image:
                compressed_path = vision.compress_image(
                    raw_path,
                    quality=self.settings.image_quality,
                    max_width=self.settings.max_image_width,
                    max_height=self.settings.max_image_height,
                )
        except Exception as exc:
            raise ComputerObservationError(f"Failed to observe the screen: {exc}") from exc

        notes: list[str] = []
        if capture.get("active_window_title"):
            notes.append(f"Active window: {capture['active_window_title']}")
        if active_request.goal:
            notes.append(f"Goal: {active_request.goal}")

        return ScreenObservation(
            screenshot_path=str(capture["path"]),
            compressed_screenshot_path=compressed_path,
            active_window_title=str(capture.get("active_window_title") or ""),
            screen_width=int(capture["screen_width"]),
            screen_height=int(capture["screen_height"]),
            capture_scope="virtual",
            notes=notes,
        )

    def _observe_monitors(
        self,
        request: ObserveRequest,
        *,
        timestamp: str,
        screenshot_dir: Path,
    ) -> ScreenObservation:
        monitors = vision.get_monitors()
        active_monitor = vision.get_active_monitor()
        active_handle = int(active_monitor["handle"])
        selected = (
            monitors
            if request.capture_scope == "all"
            else [active_monitor]
        )
        screen_images: list[ScreenImage] = []
        active_window_title = vision.get_active_window_title()

        try:
            for monitor in selected:
                monitor_index = int(monitor["index"])
                raw_path = screenshot_dir / (
                    f"screen_{timestamp}_monitor_{monitor_index}.png"
                )
                capture = vision.capture_monitor(raw_path, monitor)
                compressed_path: str | None = None
                if request.compress_image:
                    compressed_path = vision.compress_image(
                        raw_path,
                        quality=self.settings.image_quality,
                        max_width=self.settings.max_image_width,
                        max_height=self.settings.max_image_height,
                    )
                screen_images.append(
                    ScreenImage(
                        monitor_index=monitor_index,
                        screenshot_path=str(capture["path"]),
                        compressed_screenshot_path=compressed_path,
                        is_active=int(monitor["handle"]) == active_handle,
                        left=int(monitor["left"]),
                        top=int(monitor["top"]),
                        width=int(capture["screen_width"]),
                        height=int(capture["screen_height"]),
                    )
                )
        except Exception as exc:
            raise ComputerObservationError(
                f"Failed to observe individual monitors: {exc}"
            ) from exc

        primary_image = next(
            (image for image in screen_images if image.is_active),
            screen_images[0],
        )
        notes = [
            f"Capture scope: {request.capture_scope}",
            f"Captured monitors: {len(screen_images)}",
        ]
        if active_window_title:
            notes.append(f"Active window: {active_window_title}")
        if request.goal:
            notes.append(f"Goal: {request.goal}")

        return ScreenObservation(
            screenshot_path=primary_image.screenshot_path,
            compressed_screenshot_path=primary_image.compressed_screenshot_path,
            active_window_title=active_window_title,
            screen_width=primary_image.width,
            screen_height=primary_image.height,
            capture_scope=request.capture_scope,
            screen_images=screen_images,
            notes=notes,
        )
