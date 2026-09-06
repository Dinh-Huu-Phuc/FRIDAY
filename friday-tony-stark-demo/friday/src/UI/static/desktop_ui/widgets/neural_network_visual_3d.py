from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QTimer, QUrl, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QStackedWidget, QWidget

from friday.app.neural_visual import (
    NeuralTelemetryEvent,
    build_neural_scene_payload,
    serialize_neural_event,
)
from friday.src.UI.static.desktop_ui.widgets.neural_network_visual import (
    NeuralNetworkVisual,
)

try:
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover - exercised only by minimal Qt installs
    QWebEnginePage = None
    QWebEngineSettings = None
    QWebEngineView = None


class NeuralNetworkVisual3D(QStackedWidget):
    """Three.js neural telemetry view with the native 2D renderer as fallback."""

    render_ready = Signal()
    render_failed = Signal(str)
    diagnostics_changed = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        force_fallback: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setMinimumSize(480, 360)
        self._state = "online"
        self._web_ready = False
        self._shutdown = False
        self._load_failed = False
        self._load_started = False
        self._pending_events: deque[dict[str, Any]] = deque(maxlen=80)
        self._diagnostics: dict[str, Any] = {}

        self.fallback_visual = NeuralNetworkVisual(self)
        self.addWidget(self.fallback_visual)
        self.setCurrentWidget(self.fallback_visual)

        self.web_view: Any | None = None
        if force_fallback or QWebEngineView is None:
            return
        self._create_web_view()

    @property
    def state(self) -> str:
        return self._state

    @property
    def web_ready(self) -> bool:
        return self._web_ready

    @property
    def active_pulse_count(self) -> int:
        if self._web_ready:
            return int(self._diagnostics.get("pulseCount", 0))
        return self.fallback_visual.active_pulse_count

    @property
    def diagnostics(self) -> dict[str, Any]:
        return dict(self._diagnostics)

    def _create_web_view(self) -> None:
        assert QWebEngineView is not None
        assert QWebEngineSettings is not None
        self.web_view = QWebEngineView(self)
        self.web_view.setObjectName("neuralNetwork3D")
        self.web_view.page().setBackgroundColor(QColor("#02080b"))
        settings = self.web_view.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.WebGLEnabled,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            False,
        )
        self.web_view.loadFinished.connect(self._on_load_finished)
        if QWebEnginePage is not None:
            self.web_view.page().renderProcessTerminated.connect(
                lambda *_args: self._activate_fallback(
                    "The neural WebGL renderer stopped unexpectedly."
                )
            )
        self.addWidget(self.web_view)
        self._scene_file = (
            Path(__file__).resolve().parents[1]
            / "neural_3d"
            / "index.html"
        )
        if not self._scene_file.is_file():
            self._activate_fallback("The neural 3D scene files are missing.")

    def _start_web_load(self) -> None:
        if (
            self.web_view is None
            or self._load_started
            or self._load_failed
            or self._shutdown
        ):
            return
        self._load_started = True
        self.setCurrentWidget(self.web_view)
        self.web_view.load(QUrl.fromLocalFile(str(self._scene_file)))
        QTimer.singleShot(8_000, self._handle_load_timeout)

    def _on_load_finished(self, loaded: bool) -> None:
        if not loaded or self.web_view is None:
            self._activate_fallback("The neural 3D scene could not be loaded.")
            return
        payload = json.dumps(
            build_neural_scene_payload(),
            ensure_ascii=True,
            separators=(",", ":"),
        )
        self.web_view.page().runJavaScript(
            "JSON.stringify(window.fridayNeural "
            f"? window.fridayNeural.initialize({payload}) "
            ': {ready:false,webgl:false,reason:"api-unavailable"})',
            self._on_initialized,
        )

    def _on_initialized(self, result: object) -> None:
        if isinstance(result, str):
            try:
                decoded = json.loads(result)
            except json.JSONDecodeError:
                decoded = {}
        else:
            decoded = result
        diagnostics = decoded if isinstance(decoded, dict) else {}
        self._diagnostics = diagnostics
        if not diagnostics.get("ready") or not diagnostics.get("webgl"):
            self._activate_fallback("WebGL is unavailable; using the 2D neural view.")
            return
        self._web_ready = True
        self._load_failed = False
        if self.web_view is not None:
            self.setCurrentWidget(self.web_view)
        self._run_js(f"window.fridayNeural.setState({json.dumps(self._state)})")
        while self._pending_events:
            self._send_event_to_web(self._pending_events.popleft())
        self.request_diagnostics()
        self.render_ready.emit()

    def _handle_load_timeout(self) -> None:
        if not self._web_ready and not self._load_failed and not self._shutdown:
            self._activate_fallback("The neural 3D renderer timed out; using 2D.")

    def _activate_fallback(self, message: str) -> None:
        if self._shutdown or self._load_failed:
            return
        self._load_failed = True
        self._web_ready = False
        self.setCurrentWidget(self.fallback_visual)
        self.render_failed.emit(message)

    def _run_js(
        self,
        script: str,
        callback: Callable[[object], None] | None = None,
    ) -> None:
        if self.web_view is None or self._shutdown:
            return
        if callback is None:
            self.web_view.page().runJavaScript(script)
        else:
            self.web_view.page().runJavaScript(script, callback)

    def _send_event_to_web(self, payload: dict[str, Any]) -> None:
        event_json = json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
        )
        self._run_js(
            f"window.fridayNeural.ingestEvent({event_json})",
            lambda _result: self.request_diagnostics(),
        )

    def set_state(self, state: str) -> None:
        self._state = state if state in {
            "listening",
            "thinking",
            "speaking",
            "sleeping",
            "online",
        } else "online"
        self.fallback_visual.set_state(self._state)
        if self._web_ready:
            self._run_js(
                f"window.fridayNeural.setState({json.dumps(self._state)})"
            )

    def ingest_event(self, event: NeuralTelemetryEvent) -> None:
        self.fallback_visual.ingest_event(event)
        payload = serialize_neural_event(event)
        if not self._web_ready:
            self._pending_events.append(payload)
            return
        self._send_event_to_web(payload)

    def clear_telemetry(self) -> None:
        self.fallback_visual.clear_telemetry()
        self._pending_events.clear()
        self._diagnostics["pulseCount"] = 0
        if self._web_ready:
            self._run_js("window.fridayNeural.clearTelemetry()")

    def request_diagnostics(
        self,
        callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        if not self._web_ready:
            if callback is not None:
                callback(self.diagnostics)
            return

        def receive(result: object) -> None:
            try:
                decoded = json.loads(result) if isinstance(result, str) else result
            except json.JSONDecodeError:
                decoded = {}
            if isinstance(decoded, dict):
                self._diagnostics = decoded
                self.diagnostics_changed.emit(dict(decoded))
            if callback is not None:
                callback(self.diagnostics)

        self._run_js(
            "JSON.stringify(window.fridayNeural.diagnostics())",
            receive,
        )

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._start_web_load()
        if self._web_ready:
            self._run_js("window.fridayNeural.setVisible(true)")

    def hideEvent(self, event) -> None:
        if self._web_ready:
            self._run_js("window.fridayNeural.setVisible(false)")
        super().hideEvent(event)

    def shutdown(self) -> None:
        if self._shutdown:
            return
        if self._web_ready:
            self._run_js("window.fridayNeural.setVisible(false)")
        self._shutdown = True
        if self.web_view is not None:
            self.web_view.stop()
