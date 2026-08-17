from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QIcon, QImage
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from friday.app.perception.camera import (
    CameraManager,
    get_camera_manager,
    get_camera_render_fps,
    get_default_camera_index,
    get_hud_smoothing_ms,
)
from friday.app.perception.detection import SceneSnapshot
from friday.app.perception.service import (
    PerceptionService,
    get_perception_service,
)
from friday.app.spatial.exceptions import CameraUnavailableError, VisionDependencyError
from friday.runtime.vision_runtime import get_vision_runtime_decision
from friday.src.UI.static.camera_ui.feed_view import CameraFeedView
from friday.src.UI.static.camera_ui.theme import CAMERA_STYLESHEET

FRIDAY_DIR = Path(__file__).resolve().parents[4]
WINDOW_ICON = FRIDAY_DIR / "assets" / "img" / "Friday.jpg"


class CameraWindow(QMainWindow):
    closed = Signal()

    def __init__(
        self,
        manager: CameraManager | None = None,
        perception_service: PerceptionService | None = None,
    ) -> None:
        super().__init__()
        self._manager = manager or get_camera_manager()
        self._perception = perception_service or (
            get_perception_service()
            if manager is None
            else PerceptionService(manager=self._manager)
        )
        self._owner = f"camera-window:{id(self)}"
        self._active = False
        self._last_sequence = -1
        self._render_target_fps = get_camera_render_fps()
        self._render_ticks = 0
        self._render_fps = 0.0
        self._fps_started = time.monotonic()
        self._session_started_at = self._fps_started
        self._last_status_update = 0.0

        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle("FRIDAY Camera")
        self.setMinimumSize(760, 520)
        self.resize(1120, 720)
        if WINDOW_ICON.is_file():
            self.setWindowIcon(QIcon(str(WINDOW_ICON)))
        self.setStyleSheet(CAMERA_STYLESHEET)
        self._build_ui()

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(max(1, int(1000 / self._render_target_fps)))
        self._timer.timeout.connect(self._render_latest_frame)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("cameraRoot")
        shell = QVBoxLayout(root)
        shell.setContentsMargins(14, 14, 14, 14)
        shell.setSpacing(10)

        top = QFrame()
        top.setObjectName("cameraTopBar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(14, 10, 10, 10)
        brand = QLabel("FRIDAY  /  CAMERA")
        brand.setObjectName("cameraBrand")
        top_layout.addWidget(brand)
        top_layout.addStretch(1)
        self.backend_label = QLabel("VISION BACKEND / PROBING")
        self.backend_label.setObjectName("cameraMeta")
        top_layout.addWidget(self.backend_label)
        close_button = QToolButton()
        close_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton)
        )
        close_button.setToolTip("Close Camera Window")
        close_button.clicked.connect(self.close)
        top_layout.addWidget(close_button)
        shell.addWidget(top)

        self.viewport = CameraFeedView(smoothing_ms=get_hud_smoothing_ms())
        self.viewport.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.feed = self.viewport.video_label
        shell.addWidget(self.viewport, 1)

        status = QFrame()
        status.setObjectName("cameraStatusBar")
        status_layout = QHBoxLayout(status)
        status_layout.setContentsMargins(14, 9, 14, 9)
        self.state_label = QLabel("CAMERA / STANDBY")
        self.state_label.setObjectName("cameraState")
        status_layout.addWidget(self.state_label)
        status_layout.addStretch(1)
        self.target_label = QLabel("TARGET / OFFLINE")
        self.target_label.setObjectName("cameraMeta")
        status_layout.addWidget(self.target_label)
        self.fps_label = QLabel("PREVIEW / 0 FPS")
        self.fps_label.setObjectName("cameraMeta")
        status_layout.addWidget(self.fps_label)
        shell.addWidget(status)
        self.setCentralWidget(root)

    def start_preview(self, camera_index: int | None = None) -> bool:
        if self._active:
            return True
        target_index = (
            get_default_camera_index() if camera_index is None else camera_index
        )
        try:
            self._manager.acquire(self._owner, target_index)
        except (CameraUnavailableError, VisionDependencyError, ValueError) as exc:
            self.state_label.setText("CAMERA / UNAVAILABLE")
            self.feed.setText(str(exc))
            return False
        decision = get_vision_runtime_decision()
        self.backend_label.setText(
            f"VISION / {decision.backend.upper()} / {decision.profile.upper()}"
        )
        self._active = True
        self._last_sequence = -1
        self._session_started_at = time.monotonic()
        self._fps_started = time.monotonic()
        self._render_ticks = 0
        self._render_fps = 0.0
        self.state_label.setText(f"CAMERA {target_index} / LIVE")
        self.target_label.setText("TARGET / INITIALIZING")
        self._perception.start(target_index)
        self._timer.start()
        return True

    def stop_preview(self) -> None:
        self._timer.stop()
        self._perception.stop()
        if self._active:
            self._manager.release(self._owner)
            self._active = False
        self.viewport.clear_frame()
        self.state_label.setText("CAMERA / STANDBY")
        self.target_label.setText("TARGET / OFFLINE")
        self.fps_label.setText("HUD / 0 FPS")

    def _render_latest_frame(self) -> None:
        now = time.monotonic()
        status = self._manager.status()
        if status.frame_sequence != self._last_sequence:
            frame = self._manager.latest_frame(copy=True)
            if frame is not None and hasattr(frame, "shape") and len(frame.shape) >= 3:
                self._last_sequence = status.frame_sequence
                height, width, channels = frame.shape
                image = QImage(
                    frame.data,
                    width,
                    height,
                    channels * width,
                    QImage.Format.Format_BGR888,
                ).copy()
                self.viewport.set_frame(image)

        snapshot = self._perception.snapshot()
        uptime_seconds = max(0.0, now - self._session_started_at)
        self.viewport.set_snapshot(snapshot)
        self._render_ticks += 1
        elapsed = now - self._fps_started
        if elapsed >= 1.0:
            self._render_fps = self._render_ticks / elapsed
            self._render_ticks = 0
            self._fps_started = now
        self.viewport.set_metrics(
            camera_index=status.camera_index or 0,
            source_fps=status.capture_fps,
            render_fps=self._render_fps,
            uptime_seconds=uptime_seconds,
        )
        self.viewport.advance_hud(now)
        if now - self._last_status_update >= 0.2:
            self._last_status_update = now
            self._update_scene_labels(snapshot, status.capture_fps, uptime_seconds)

    def _update_scene_labels(
        self,
        snapshot: SceneSnapshot,
        source_fps: float,
        uptime_seconds: float,
    ) -> None:
        latency = (
            f"{snapshot.inference_ms:.0f} MS"
            if snapshot.inference_ms is not None
            else "--"
        )
        self.fps_label.setText(
            f"HUD {self._render_fps:.1f} | SRC {source_fps:.1f} | "
            f"AI {latency} | UP {self._format_uptime(uptime_seconds)}"
        )
        if snapshot.status == "loading":
            self.target_label.setText("TARGET / LOADING MODEL")
            return
        if snapshot.status == "disabled":
            self.target_label.setText("TARGET / DISABLED")
            return
        if snapshot.status == "error":
            self.target_label.setText("TARGET / MODEL ERROR")
            return
        if snapshot.status != "ready":
            self.target_label.setText("TARGET / SEARCHING")
            return

        if snapshot.model_name:
            self.backend_label.setText(f"VISION / {snapshot.model_name.upper()} / LOCAL")
        target = snapshot.target_lock.target
        if target is None:
            self.target_label.setText(
                f"SEARCHING / {len(snapshot.objects):02d} OBJECTS"
            )
            return
        state = snapshot.target_lock.state.value.upper()
        self.target_label.setText(
            f"{state} / {target.label.upper()} #{target.track_id:02d} / "
            f"{target.confidence:.0%}"
        )

    @staticmethod
    def _format_uptime(uptime_seconds: float) -> str:
        total_seconds = max(0, round(uptime_seconds))
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def closeEvent(self, event: QCloseEvent) -> None:
        self.stop_preview()
        self.closed.emit()
        super().closeEvent(event)
