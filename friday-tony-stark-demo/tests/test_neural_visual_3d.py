from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from friday.app.neural_visual import (
    NeuralEventStatus,
    NeuralNodeId,
    NeuralTelemetryEvent,
)
from friday.src.UI.static.desktop_ui.widgets.neural_network_visual_3d import (
    NeuralNetworkVisual3D,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENE_ROOT = (
    PROJECT_ROOT
    / "friday"
    / "src"
    / "UI"
    / "static"
    / "desktop_ui"
    / "neural_3d"
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _sample_event() -> NeuralTelemetryEvent:
    return NeuralTelemetryEvent(
        trace_id="wrapper-fallback-test",
        source_node=NeuralNodeId.TEXT_INPUT,
        target_node=NeuralNodeId.INTENT_ROUTER,
        event_type="intent.routing.started",
        summary="Open Neural Network",
        status=NeuralEventStatus.ACTIVE,
        duration_ms=12.4,
    )


def test_3d_wrapper_preserves_the_native_2d_runtime_contract() -> None:
    _app()
    visual = NeuralNetworkVisual3D(force_fallback=True)

    visual.set_state("thinking")
    visual.ingest_event(_sample_event())

    assert visual.state == "thinking"
    assert visual.fallback_visual.state == "thinking"
    assert visual.active_pulse_count == 1
    assert not visual.web_ready

    visual.clear_telemetry()
    assert visual.active_pulse_count == 0
    visual.shutdown()


def test_3d_scene_is_complete_and_uses_only_vendored_three_js() -> None:
    scene_js = (SCENE_ROOT / "scene.js").read_text(encoding="utf-8")
    html = (SCENE_ROOT / "index.html").read_text(encoding="utf-8")

    assert (SCENE_ROOT / "vendor" / "three.module.min.js").stat().st_size > 100_000
    assert (SCENE_ROOT / "vendor" / "three.core.min.js").stat().st_size > 100_000
    assert (SCENE_ROOT / "vendor" / "THREE-LICENSE.txt").is_file()
    assert 'from "./vendor/three.module.min.js"' in scene_js
    assert "http://" not in scene_js
    assert "https://" not in scene_js
    assert "window.fridayNeural" in scene_js
    assert "ingestEvent" in scene_js
    assert "diagnostics" in scene_js
    assert "createBrainTissue" in scene_js
    assert "createCircuitLattice" in scene_js
    assert "createCorticalFolds" in scene_js
    assert "createDendrites" in scene_js
    assert "GridHelper" not in scene_js
    assert "PlaneGeometry" not in scene_js
    assert '<script type="module" src="./scene.js"></script>' in html
