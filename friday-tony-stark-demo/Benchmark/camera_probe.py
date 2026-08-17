from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")


@dataclass(frozen=True, slots=True)
class CameraProbeResult:
    index: int
    available: bool
    width: int = 0
    height: int = 0


def probe_camera(index: int) -> CameraProbeResult:
    import cv2  # type: ignore

    if hasattr(cv2, "setLogLevel"):
        cv2.setLogLevel(0)
    capture = None
    try:
        if os.name == "nt":
            capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        else:
            capture = cv2.VideoCapture(index)
        if not capture.isOpened():
            return CameraProbeResult(index=index, available=False)
        frame = None
        for _ in range(12):
            ok, candidate = capture.read()
            if ok and candidate is not None:
                frame = candidate
                break
        if frame is None:
            return CameraProbeResult(index=index, available=False)
        height, width = frame.shape[:2]
        return CameraProbeResult(
            index=index,
            available=True,
            width=int(width),
            height=int(height),
        )
    finally:
        if capture is not None:
            capture.release()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find OpenCV camera indexes for FRIDAY."
    )
    parser.add_argument("--max-index", type=int, default=4)
    args = parser.parse_args()

    print("\nFRIDAY CAMERA PROBE")
    print("=" * 46)
    available: list[CameraProbeResult] = []
    for index in range(max(0, args.max_index) + 1):
        result = probe_camera(index)
        if result.available:
            available.append(result)
            print(f"Camera {index}: AVAILABLE ({result.width}x{result.height})")
        else:
            print(f"Camera {index}: unavailable")
    print("=" * 46)
    if available:
        indexes = ", ".join(str(item.index) for item in available)
        print(f"Available indexes: {indexes}")
        print("Set FRIDAY_CAMERA_INDEX in .env, then restart FRIDAY.")
        return 0
    print("No camera returned a frame.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
