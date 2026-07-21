"""PySide6 process that paints two aqua trails around every connected screen."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
from ctypes import wintypes
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QElapsedTimer, QLineF, QPointF, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QPaintEvent, QPainter, QPen, QScreen
from PySide6.QtWidgets import QApplication, QWidget

from friday.app.computer.capture_effect.geometry import perimeter_length, trail_points


WINDOW_TITLE = "FRIDAY Capture Effect"
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040


class CaptureOverlay(QWidget):
    def __init__(self, screen: QScreen, *, duration_ms: int) -> None:
        super().__init__()
        self.screen = screen
        self.duration_ms = max(1, int(duration_ms))
        self.elapsed = QElapsedTimer()
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.update)
        self.capture_excluded = False

        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def start(self) -> None:
        geometry = self.screen.geometry()
        self.setScreen(self.screen)
        self.setGeometry(geometry)
        self.show()
        self.setGeometry(geometry)
        self.raise_()
        self.capture_excluded = _configure_native_window(int(self.winId()))
        self.elapsed.start()
        self.timer.start()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        width = float(self.width())
        height = float(self.height())
        if width <= 2 or height <= 2:
            return

        progress = min(1.0, self.elapsed.elapsed() / self.duration_ms)
        opacity = _animation_opacity(progress)
        perimeter = perimeter_length(width, height)
        travel = progress * perimeter * 1.18

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        border_color = QColor(79, 255, 238, round(45 * opacity))
        painter.setPen(QPen(border_color, 1.2))
        painter.drawRect(QRectF(5.0, 5.0, width - 10.0, height - 10.0))

        self._draw_trail(painter, travel, 1, opacity)
        self._draw_trail(painter, (perimeter / 2.0) - travel, -1, opacity)
        painter.end()

    def _draw_trail(
        self,
        painter: QPainter,
        head_distance: float,
        direction: int,
        opacity: float,
    ) -> None:
        points = trail_points(
            head_distance=head_distance,
            direction=direction,
            width=float(self.width()),
            height=float(self.height()),
        )
        for index in range(len(points) - 1):
            strength = ((index + 1) / (len(points) - 1)) ** 1.65
            start = QPointF(*points[index])
            end = QPointF(*points[index + 1])
            line = QLineF(start, end)
            for line_width, base_alpha in ((14.0, 22), (6.0, 58), (2.2, 235)):
                color = QColor(79, 255, 238, round(base_alpha * strength * opacity))
                pen = QPen(color, line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawLine(line)


def _animation_opacity(progress: float) -> float:
    fade_in = min(1.0, progress / 0.10)
    fade_out = min(1.0, max(0.0, (1.0 - progress) / 0.18))
    return fade_in * fade_out


def _configure_native_window(hwnd: int) -> bool:
    if os.name != "nt":
        return False
    user32 = ctypes.windll.user32
    get_style = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    set_style = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
    get_style.argtypes = [wintypes.HWND, ctypes.c_int]
    get_style.restype = ctypes.c_ssize_t
    set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    set_style.restype = ctypes.c_ssize_t
    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
    style = int(get_style(hwnd, GWL_EXSTYLE))
    set_style(
        hwnd,
        GWL_EXSTYLE,
        style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
    )
    user32.SetWindowPos(
        hwnd,
        HWND_TOPMOST,
        0,
        0,
        0,
        0,
        SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
    )
    return bool(user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE))


def _write_state(path: Path, *, windows: list[CaptureOverlay]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pid": os.getpid(),
        "ready": bool(windows),
        "screen_count": len(windows),
        "capture_excluded_count": sum(window.capture_excluded for window in windows),
    }
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(path)


def _save_preview(windows: list[CaptureOverlay], path: Path) -> None:
    if not windows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    windows[0].grab().save(str(path), "PNG")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FRIDAY screen capture edge effect")
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--duration-ms", type=int, default=1100)
    parser.add_argument("--preview-path", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(argv if argv is not None else sys.argv[1:]))
    application = QApplication(sys.argv[:1])
    application.setApplicationName(WINDOW_TITLE)
    application.setQuitOnLastWindowClosed(False)

    windows = [
        CaptureOverlay(screen, duration_ms=args.duration_ms)
        for screen in application.screens()
    ]
    for window in windows:
        window.start()
    application.processEvents()
    _write_state(args.state_path, windows=windows)

    if args.preview_path:
        QTimer.singleShot(
            min(350, max(120, args.duration_ms // 3)),
            lambda: _save_preview(windows, args.preview_path),
        )
    QTimer.singleShot(max(1, args.duration_ms), application.quit)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
