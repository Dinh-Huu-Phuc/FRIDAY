"""Opt-in local benchmark. No camera access, image uploads, or model downloads.

Default: synthetic structured-state timings only. --image or --synthetic-image
also runs real local Ollama requests. --cold explicitly unloads the selected
model first; do not use it while other clients are using that model.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import replace
from pathlib import Path

from friday.app.perception.detection import BoundingBox, SceneSnapshot, TrackedObject
from friday.app.perception.reasoning.gemma_vision import GemmaVisionClient
from friday.app.perception.reasoning.keyframes import KeyframeStore
from friday.app.perception.reasoning.vision_router import VisionRouter
from friday.app.perception.scene import SceneStateStore
from friday.app.perception.world import WorldSnapshot


class BenchmarkPerception:
    def __init__(self, frame=None, *, structured=True):
        self.frame = frame
        self.store = SceneStateStore()
        self.keyframes = KeyframeStore()
        self.sequence = 1
        self.store.update(
            SceneSnapshot(
                status="ready",
                captured_at=time.time(),
                frame_width=1280,
                frame_height=720,
                objects=(
                    TrackedObject(1, 0, "person", 0.95, BoundingBox(20, 20, 200, 400)),
                )
                if structured
                else (),
            )
        )

    def snapshot(self):
        return self.store.snapshot()

    def temporal_snapshot(self):
        return self.store.temporal_snapshot()

    def world_snapshot(self):
        return WorldSnapshot()

    def describe_world(self, *, question=""):
        return ""

    def describe_scene(self):
        return self.store.describe()

    def capture_keyframe(self, *, timings=None):
        if self.frame is None:
            return None
        start = time.perf_counter()
        frame = self.frame.copy()
        if timings is not None:
            timings["frame_acquisition_ms"] = (time.perf_counter() - start) * 1000
        self.sequence += 1
        snapshot = replace(
            self.snapshot(),
            sequence=self.sequence,
            captured_at=time.time(),
            frame_height=frame.shape[0],
            frame_width=frame.shape[1],
        )
        return self.keyframes.consider(
            frame,
            snapshot,
            self.temporal_snapshot(),
            force=True,
            timings=timings,
        )


def run_benchmark(*, frame=None, runs=2, fast_samples=100, cold=False) -> dict:
    source = BenchmarkPerception()
    router = VisionRouter(source, clock=lambda: source.snapshot().captured_at)
    fast = [
        router.analyze_sync("What objects can you see?").timings
        for _ in range(fast_samples)
    ]
    values = sorted(item.total_ms for item in fast)
    report = {
        "fast_path": {
            "input": "synthetic fresh structured state; not detector inference",
            "samples": len(values),
            "median_ms": statistics.median(values),
            "p95_ms": values[max(0, int(len(values) * 0.95) - 1)],
            "gemma_invoked": any(item.gemma_invoked for item in fast),
        },
        "semantic_requests": [],
        "notes": ["No prompts, answers, or image bytes are included in this report."],
    }
    if frame is None:
        report["notes"].append(
            "Cold/warm VLM latency not measured: supply --image or --synthetic-image."
        )
        return report
    client = GemmaVisionClient()
    if cold:
        import httpx

        response = httpx.post(
            client.endpoint.removesuffix("/chat") + "/generate",
            json={"model": client.model, "keep_alive": 0},
            timeout=30,
        )
        response.raise_for_status()
    router = VisionRouter(
        BenchmarkPerception(frame, structured=False),
        client=client,
        enabled=True,
        cache_seconds=0,
    )
    report["settings"] = {
        "keep_alive": client.keep_alive,
        "num_predict": client.num_predict,
        "maximum_image_edge": 896,
    }
    report["notes"].append(
        "Semantic acquisition measures a copy of the supplied image, not webcam acquisition. Repeated calls use the same image and may benefit from prompt caching."
    )
    for index in range(runs):
        result = router.analyze_sync("Describe what is visible in this image briefly.")
        report["semantic_requests"].append(
            {
                "run": index + 1,
                "condition": "cold_requested"
                if cold and index == 0
                else "first"
                if index == 0
                else "repeat",
                "status": result.status.value,
                "timings": result.timings.to_dict(),
            }
        )
    return report


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[4] / ".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument(
        "--image",
        type=Path,
        help="Local image sent only to local Ollama; not saved in the report",
    )
    inputs.add_argument(
        "--synthetic-image",
        action="store_true",
        help="Use a non-personal geometric test image",
    )
    parser.add_argument(
        "--cold",
        action="store_true",
        help="Unload the selected model first; may disrupt other clients",
    )
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--fast-samples", type=int, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.runs <= 10 or not 1 <= args.fast_samples <= 10000:
        parser.error("runs must be 1..10 and fast-samples must be 1..10000")
    if args.cold and not (args.image or args.synthetic_image):
        parser.error("--cold requires an image option")
    frame = None
    if args.image or args.synthetic_image:
        import cv2
        import numpy as np

        if args.image:
            frame = cv2.imdecode(
                np.fromfile(args.image, dtype=np.uint8), cv2.IMREAD_COLOR
            )
            if frame is None:
                parser.error("Unable to decode the supplied image")
        else:
            frame = np.full((720, 1280, 3), 235, dtype=np.uint8)
            cv2.rectangle(frame, (150, 180), (500, 550), (30, 100, 220), -1)
            cv2.circle(frame, (880, 360), 160, (210, 100, 30), -1)
    report = run_benchmark(
        frame=frame, runs=args.runs, fast_samples=args.fast_samples, cold=args.cold
    )
    report["image_kind"] = (
        "synthetic geometry"
        if args.synthetic_image
        else "user supplied"
        if args.image
        else "none"
    )
    serialized = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
