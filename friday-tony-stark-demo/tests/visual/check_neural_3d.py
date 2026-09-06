from __future__ import annotations

import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np
from playwright.sync_api import Page, sync_playwright

from friday.app.neural_visual import build_neural_scene_payload


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE_ROOT = (
    PROJECT_ROOT
    / "friday"
    / "src"
    / "UI"
    / "static"
    / "desktop_ui"
    / "neural_3d"
)
OUTPUT_ROOT = Path(__file__).resolve().parent / "output"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args) -> None:
        return


def sample_events(payload: dict) -> list[dict]:
    events = []
    for index, edge in enumerate(payload["edges"][:12]):
        events.append(
            {
                "eventId": f"visual-{index}",
                "traceId": "visual-check",
                "sourceNode": edge["source"],
                "targetNode": edge["target"],
                "eventType": "runtime.transfer",
                "summary": f"Telemetry from {edge['source']} to {edge['target']}",
                "status": "success" if index % 3 else "active",
                "durationMs": 8.0 + index * 1.7,
                "createdAt": "2026-08-27T00:00:00.000+00:00",
            }
        )
    return events


def assert_canvas_has_scene(page: Page) -> dict[str, float]:
    canvas_png = page.locator("#neural-canvas").screenshot()
    image = cv2.imdecode(np.frombuffer(canvas_png, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert image is not None
    brightness = image.max(axis=2)
    non_black_ratio = float(np.mean(brightness > 18))
    contrast = float(image.std())
    colorful_ratio = float(np.mean((image.max(axis=2) - image.min(axis=2)) > 16))
    assert non_black_ratio > 0.025
    assert contrast > 8.0
    assert colorful_ratio > 0.008
    return {
        "nonBlackRatio": round(non_black_ratio, 4),
        "contrast": round(contrast, 2),
        "colorfulRatio": round(colorful_ratio, 4),
    }


def assert_layout_is_contained(page: Page) -> None:
    layout = page.evaluate(
        """
        () => {
          const viewport = { width: innerWidth, height: innerHeight };
          const selectors = ['.scene-header', '.layer-legend', '.runtime-strip'];
          const boxes = selectors.map((selector) => {
            const rect = document.querySelector(selector).getBoundingClientRect();
            return { selector, left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom };
          });
          return {
            viewport,
            boxes,
            labels: [...document.querySelectorAll('.node-label')]
              .filter((label) => label.dataset.hidden !== 'true')
              .map((label) => {
                const rect = label.getBoundingClientRect();
                return { text: label.textContent, left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom };
              }),
            horizontalOverflow: document.documentElement.scrollWidth - innerWidth,
            verticalOverflow: document.documentElement.scrollHeight - innerHeight,
          };
        }
        """
    )
    assert layout["horizontalOverflow"] <= 0
    assert layout["verticalOverflow"] <= 0
    for box in layout["boxes"]:
        assert box["left"] >= -1
        assert box["top"] >= -1
        assert box["right"] <= layout["viewport"]["width"] + 1
        assert box["bottom"] <= layout["viewport"]["height"] + 1
    for label in layout["labels"]:
        assert label["left"] >= -1, label
        assert label["right"] <= layout["viewport"]["width"] + 1, label
        assert label["top"] >= -1, label
        assert label["bottom"] <= layout["viewport"]["height"] + 1, label


def exercise_viewport(page: Page, name: str, width: int, height: int, base_url: str) -> dict:
    page.set_viewport_size({"width": width, "height": height})
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base_url, wait_until="networkidle")
    page.wait_for_function("() => Boolean(window.fridayNeural)")

    payload = build_neural_scene_payload()
    diagnostics = page.evaluate(
        "payload => window.fridayNeural.initialize(payload)",
        payload,
    )
    assert diagnostics["ready"]
    assert diagnostics["webgl"]
    assert diagnostics["nodeCount"] == len(payload["nodes"])
    assert diagnostics["edgeCount"] == len(payload["edges"])

    page.evaluate(
        "events => events.forEach(event => window.fridayNeural.ingestEvent(event))",
        sample_events(payload),
    )
    page.evaluate("() => window.fridayNeural.setState('thinking')")
    page.wait_for_timeout(650)

    center = page.locator("#neural-canvas").bounding_box()
    assert center is not None
    page.mouse.move(center["x"] + center["width"] / 2, center["y"] + center["height"] / 2)
    page.mouse.click(center["x"] + center["width"] / 2, center["y"] + center["height"] / 2)
    page.wait_for_timeout(100)

    diagnostics = page.evaluate("() => window.fridayNeural.diagnostics()")
    assert diagnostics["renderCalls"] > 0
    assert diagnostics["canvasWidth"] > 0
    assert diagnostics["canvasHeight"] > 0
    assert diagnostics["state"] == "thinking"
    assert diagnostics["pulseCount"] > 0
    assert not errors, errors
    assert_layout_is_contained(page)
    pixels = assert_canvas_has_scene(page)

    screenshot_path = OUTPUT_ROOT / f"neural-3d-{name}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    return {
        "viewport": {"width": width, "height": height},
        "diagnostics": diagnostics,
        "pixels": pixels,
        "screenshot": str(screenshot_path),
    }


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    handler = partial(QuietHandler, directory=str(SCENE_ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}/index.html"

    results: dict[str, dict] = {}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel="chrome",
                headless=True,
                args=[
                    "--ignore-gpu-blocklist",
                    "--enable-webgl",
                    "--use-angle=swiftshader",
                ],
            )
            try:
                page = browser.new_page()
                results["desktop"] = exercise_viewport(
                    page,
                    "desktop",
                    1440,
                    900,
                    base_url,
                )
                page.close()
                page = browser.new_page()
                results["compact"] = exercise_viewport(
                    page,
                    "compact",
                    390,
                    844,
                    base_url,
                )
                page.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
