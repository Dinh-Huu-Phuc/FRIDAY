from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np

os.environ.pop("QTWEBENGINE_CHROMIUM_FLAGS", None)

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from friday.app.neural_visual import (
    NeuralEventStatus,
    NeuralNodeId,
    NeuralTelemetryEvent,
)
from friday.src.UI.static.desktop_ui.widgets.neural_network_visual_3d import (
    NeuralNetworkVisual3D,
)


OUTPUT_PATH = Path(__file__).resolve().parent / "output" / "neural-3d-pyside6.png"


def main() -> None:
    app = QApplication.instance() or QApplication([])
    visual = NeuralNetworkVisual3D()
    visual.resize(1100, 680)
    result: dict[str, object] = {"ready": False, "error": ""}
    loop = QEventLoop()

    def failed(message: str) -> None:
        result["error"] = f"{message} diagnostics={visual.diagnostics}"
        loop.quit()

    def capture(diagnostics: dict) -> None:
        result["diagnostics"] = diagnostics
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        assert visual.grab().save(str(OUTPUT_PATH), "PNG")
        loop.quit()

    def ready() -> None:
        result["ready"] = True
        visual.ingest_event(
            NeuralTelemetryEvent(
                trace_id="qt-direct-check",
                source_node=NeuralNodeId.TEXT_INPUT,
                target_node=NeuralNodeId.INTENT_ROUTER,
                event_type="intent.routing.started",
                summary="Direct PySide6 WebEngine verification",
                status=NeuralEventStatus.SUCCESS,
                duration_ms=11.8,
            )
        )
        visual.set_state("thinking")
        QTimer.singleShot(900, lambda: visual.request_diagnostics(capture))

    visual.render_failed.connect(failed)
    visual.render_ready.connect(ready)
    QTimer.singleShot(14_000, lambda: failed("Timed out waiting for the PySide6 renderer"))
    visual.show()
    loop.exec()

    try:
        assert result["ready"], result["error"]
        diagnostics = result.get("diagnostics")
        assert isinstance(diagnostics, dict)
        assert diagnostics["ready"]
        assert diagnostics["webgl"]
        assert diagnostics["nodeCount"] == 16
        assert diagnostics["edgeCount"] == 25
        assert diagnostics["renderCalls"] > 0

        image = cv2.imread(str(OUTPUT_PATH), cv2.IMREAD_COLOR)
        assert image is not None
        non_black_ratio = float(np.mean(image.max(axis=2) > 18))
        assert non_black_ratio > 0.025
        print(
            {
                "diagnostics": diagnostics,
                "nonBlackRatio": round(non_black_ratio, 4),
                "screenshot": str(OUTPUT_PATH),
            }
        )
    finally:
        visual.shutdown()
        visual.close()
        app.processEvents()


if __name__ == "__main__":
    main()
