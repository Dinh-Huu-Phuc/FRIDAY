from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from friday.app.computer.config.settings import ComputerSettings
from friday.app.computer.schemas.entities import ScreenImage, ScreenObservation
from friday.app.computer.schemas.requests import ObserveRequest
from friday.app.computer.service.observer import ComputerObserver
from friday.app.computer.service import screen_understanding


MONITORS = [
    {
        "index": 1,
        "handle": 11,
        "left": 0,
        "top": 0,
        "right": 1920,
        "bottom": 1080,
        "width": 1920,
        "height": 1080,
        "is_primary": True,
    },
    {
        "index": 2,
        "handle": 22,
        "left": 1920,
        "top": 0,
        "right": 3840,
        "bottom": 1080,
        "width": 1920,
        "height": 1080,
        "is_primary": False,
    },
]


def _fake_capture(path: Path, monitor: dict) -> dict:
    path.write_bytes(f"raw-monitor-{monitor['index']}".encode())
    return {
        "path": str(path),
        "screen_width": monitor["width"],
        "screen_height": monitor["height"],
    }


def _fake_compress(path: Path, **_kwargs) -> str:
    compressed = path.with_name(f"{path.stem}_compressed.jpg")
    compressed.write_bytes(b"compressed")
    return str(compressed)


def test_active_scope_captures_only_the_foreground_monitor(tmp_path) -> None:
    observer = ComputerObserver(settings=ComputerSettings(screenshot_dir=tmp_path))
    with patch.object(
        __import__("friday.app.computer.service.observer", fromlist=["vision"]).vision,
        "get_monitors",
        return_value=MONITORS,
    ), patch(
        "friday.app.computer.service.observer.vision.get_active_monitor",
        return_value=MONITORS[1],
    ), patch(
        "friday.app.computer.service.observer.vision.get_active_window_title",
        return_value="Active app",
    ), patch(
        "friday.app.computer.service.observer.vision.capture_monitor",
        side_effect=_fake_capture,
    ) as capture, patch(
        "friday.app.computer.service.observer.vision.compress_image",
        side_effect=_fake_compress,
    ):
        result = observer.observe(ObserveRequest(capture_scope="active"))

    assert result.capture_scope == "active"
    assert len(result.screen_images) == 1
    assert result.screen_images[0].monitor_index == 2
    assert result.screen_images[0].is_active is True
    assert capture.call_count == 1


def test_all_scope_captures_each_monitor_as_a_separate_image(tmp_path) -> None:
    observer = ComputerObserver(settings=ComputerSettings(screenshot_dir=tmp_path))
    with patch(
        "friday.app.computer.service.observer.vision.get_monitors",
        return_value=MONITORS,
    ), patch(
        "friday.app.computer.service.observer.vision.get_active_monitor",
        return_value=MONITORS[1],
    ), patch(
        "friday.app.computer.service.observer.vision.get_active_window_title",
        return_value="Active app",
    ), patch(
        "friday.app.computer.service.observer.vision.capture_monitor",
        side_effect=_fake_capture,
    ), patch(
        "friday.app.computer.service.observer.vision.compress_image",
        side_effect=_fake_compress,
    ):
        result = observer.observe(ObserveRequest(capture_scope="all"))

    assert [image.monitor_index for image in result.screen_images] == [1, 2]
    assert [image.is_active for image in result.screen_images] == [False, True]
    assert result.screenshot_path == result.screen_images[1].screenshot_path


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self) -> bytes:
        return json.dumps({"message": {"content": "Two screens are visible."}}).encode()


def test_vision_payload_contains_each_monitor_image_and_removes_raw_files(tmp_path) -> None:
    images = []
    for index in (1, 2):
        raw = tmp_path / f"monitor-{index}.png"
        compressed = tmp_path / f"monitor-{index}.jpg"
        raw.write_bytes(f"raw-{index}".encode())
        compressed.write_bytes(f"jpeg-{index}".encode())
        images.append(
            ScreenImage(
                monitor_index=index,
                screenshot_path=str(raw),
                compressed_screenshot_path=str(compressed),
                is_active=index == 2,
                left=0,
                top=0,
                width=1920,
                height=1080,
            )
        )
    observation = ScreenObservation(
        observed_at=datetime.now(timezone.utc),
        screenshot_path=images[1].screenshot_path,
        compressed_screenshot_path=images[1].compressed_screenshot_path,
        active_window_title="Browser",
        screen_width=1920,
        screen_height=1080,
        capture_scope="all",
        screen_images=images,
    )
    captured_request = {}

    def fake_urlopen(request, timeout):
        captured_request["payload"] = json.loads(request.data)
        captured_request["timeout"] = timeout
        return _Response()

    with patch.object(
        screen_understanding, "_observe_current_screen", return_value=observation
    ), patch.object(screen_understanding, "_queue_cloud_archive"), patch.object(
        screen_understanding, "urlopen", side_effect=fake_urlopen
    ):
        answer = screen_understanding._analyze_screen_sync(
            "What is displayed across all my screens?"
        )

    message = captured_request["payload"]["messages"][0]
    assert answer == "Two screens are visible."
    assert len(message["images"]) == 2
    assert "Monitor 2 (active)" in message["content"]
    assert all(not Path(image.screenshot_path).exists() for image in images)
    assert all(Path(image.compressed_screenshot_path).exists() for image in images)
