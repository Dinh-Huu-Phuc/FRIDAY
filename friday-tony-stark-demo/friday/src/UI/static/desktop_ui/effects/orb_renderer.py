from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)

from friday.src.UI.static.desktop_ui.theme_tokens import COLORS


@dataclass(frozen=True)
class _OrbPoint:
    x: float
    y: float
    size: float
    alpha: int


class OrbRenderer:
    """Paint a cached, lightweight sci-fi orb without blur effects."""

    def __init__(self) -> None:
        self._stars = tuple(
            _OrbPoint(
                x=((index * 47) % 997) / 997,
                y=((index * 83 + 29) % 991) / 991,
                size=0.7 + (index % 4) * 0.35,
                alpha=20 + (index % 7) * 7,
            )
            for index in range(72)
        )
        self._nodes = tuple(
            QPointF(
                math.cos(index * 2.39996) * (0.18 + (index % 7) * 0.105),
                math.sin(index * 2.39996) * (0.22 + (index % 5) * 0.145),
            )
            for index in range(36)
        )
        self._edges = tuple(
            (index, (index + offset) % len(self._nodes))
            for index in range(len(self._nodes))
            for offset in (5, 11)
            if index < (index + offset) % len(self._nodes)
        )

    def paint(
        self,
        painter: QPainter,
        bounds: QRectF,
        *,
        phase: float,
        state: str,
        audio_level: float,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(bounds, QColor(COLORS.canvas_deep))

        center = QPointF(bounds.center().x(), bounds.center().y() - 4)
        radius = max(112.0, min(260.0, min(bounds.width(), bounds.height()) * 0.34))
        self._paint_background(painter, bounds, center, radius, phase)
        self._paint_energy_wave(painter, bounds, center, radius, phase, audio_level)
        self._paint_orb(painter, center, radius, phase, state, audio_level)
        self._paint_base(painter, center, radius, phase)
        self._paint_identity(painter, center, state)

    def _paint_background(
        self,
        painter: QPainter,
        bounds: QRectF,
        center: QPointF,
        radius: float,
        phase: float,
    ) -> None:
        aura = QRadialGradient(center, radius * 2.4)
        aura.setColorAt(0.0, QColor(32, 74, 152, 38))
        aura.setColorAt(0.45, QColor(18, 42, 92, 18))
        aura.setColorAt(1.0, QColor(2, 6, 13, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(aura)
        painter.drawEllipse(center, radius * 2.35, radius * 1.65)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        for index, star in enumerate(self._stars):
            pulse = 0.65 + 0.35 * math.sin(math.radians(phase * 0.5 + index * 23))
            color = QColor(COLORS.blue if index % 4 else COLORS.cyan)
            color.setAlpha(round(star.alpha * pulse))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(
                QPointF(
                    bounds.left() + star.x * bounds.width(),
                    bounds.top() + star.y * bounds.height(),
                ),
                star.size,
                star.size,
            )

    def _paint_energy_wave(
        self,
        painter: QPainter,
        bounds: QRectF,
        center: QPointF,
        radius: float,
        phase: float,
        audio_level: float,
    ) -> None:
        amplitude = 10.0 + audio_level * 24.0
        for band, color_name in enumerate((COLORS.blue, COLORS.cyan, COLORS.violet)):
            path = QPainterPath()
            step = max(8.0, bounds.width() / 110.0)
            x = bounds.left()
            while x <= bounds.right():
                distance = abs(x - center.x())
                envelope = max(0.12, 1.0 - distance / max(1.0, bounds.width() * 0.58))
                wave = math.sin((x * (0.027 + band * 0.004)) + phase * 0.035 + band * 1.9)
                y = center.y() + wave * amplitude * envelope * (1.0 + band * 0.32)
                if x == bounds.left():
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
                x += step
            color = QColor(color_name)
            color.setAlpha(46 - band * 8)
            painter.setPen(QPen(color, 1.0 + (band == 1) * 0.6))
            painter.drawPath(path)

        fade = QLinearGradient(bounds.left(), center.y(), bounds.right(), center.y())
        fade.setColorAt(0.0, QColor(49, 141, 255, 0))
        fade.setColorAt(0.35, QColor(49, 141, 255, 24))
        fade.setColorAt(0.5, QColor(80, 232, 255, 70))
        fade.setColorAt(0.65, QColor(168, 92, 255, 24))
        fade.setColorAt(1.0, QColor(168, 92, 255, 0))
        painter.setPen(QPen(fade, 1.0))
        painter.drawLine(QPointF(bounds.left(), center.y()), QPointF(bounds.right(), center.y()))

    def _paint_orb(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        phase: float,
        state: str,
        audio_level: float,
    ) -> None:
        state_boost = 1.0 + (
            0.055 if state == "thinking" else 0.035 if state == "speaking" else 0.0
        )
        pulse = state_boost + math.sin(math.radians(phase * 2.0)) * (0.012 + audio_level * 0.022)
        orb_radius = radius * pulse

        outer_glow = QRadialGradient(center, orb_radius * 1.28)
        outer_glow.setColorAt(0.56, QColor(47, 102, 255, 18))
        outer_glow.setColorAt(0.76, QColor(80, 232, 255, 28))
        outer_glow.setColorAt(0.9, QColor(240, 82, 212, 18))
        outer_glow.setColorAt(1.0, QColor(2, 6, 13, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(outer_glow)
        painter.drawEllipse(center, orb_radius * 1.3, orb_radius * 1.3)

        body = QRadialGradient(
            QPointF(center.x() - orb_radius * 0.26, center.y() - orb_radius * 0.32),
            orb_radius * 1.2,
        )
        body.setColorAt(0.0, QColor(23, 64, 130, 175))
        body.setColorAt(0.34, QColor(6, 23, 59, 238))
        body.setColorAt(0.68, QColor(5, 11, 31, 252))
        body.setColorAt(1.0, QColor(1, 4, 12, 255))
        painter.setBrush(body)
        painter.setPen(QPen(QColor(COLORS.cyan), 1.3))
        painter.drawEllipse(center, orb_radius, orb_radius)

        clip_path = QPainterPath()
        clip_path.addEllipse(center, orb_radius * 0.97, orb_radius * 0.97)
        painter.save()
        painter.setClipPath(clip_path)
        self._paint_color_fields(painter, center, orb_radius, phase)
        self._paint_color_currents(painter, center, orb_radius, phase)
        self._paint_sphere_grid(painter, center, orb_radius, phase)
        self._paint_network(painter, center, orb_radius, phase)
        painter.restore()

        rim = QConicalGradient(center, phase * 0.12)
        rim.setColorAt(0.0, QColor(COLORS.cyan))
        rim.setColorAt(0.24, QColor(COLORS.blue))
        rim.setColorAt(0.5, QColor(COLORS.magenta))
        rim.setColorAt(0.72, QColor(COLORS.amber))
        rim.setColorAt(1.0, QColor(COLORS.cyan))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QBrush(rim), 2.0))
        painter.drawEllipse(center, orb_radius * 1.005, orb_radius * 1.005)

        ring_rect = QRectF(
            center.x() - orb_radius * 1.015,
            center.y() - orb_radius * 1.015,
            orb_radius * 2.03,
            orb_radius * 2.03,
        )
        for index, color_name in enumerate(
            (COLORS.cyan, COLORS.blue, COLORS.magenta, COLORS.amber)
        ):
            color = QColor(color_name)
            color.setAlpha(215 - index * 28)
            pen = QPen(color, 2.3 if index == 0 else 1.6)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            start = int((phase * (0.56 if index % 2 == 0 else -0.43) + index * 87) * 16)
            painter.drawArc(
                ring_rect.adjusted(index, index, -index, -index),
                start,
                int((38 + index * 17) * 16),
            )

    def _paint_color_fields(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        phase: float,
    ) -> None:
        field_specs = (
            (-0.52, -0.1, COLORS.blue, 84),
            (0.4, -0.36, COLORS.cyan, 72),
            (-0.18, 0.46, COLORS.magenta, 68),
            (0.54, 0.34, COLORS.amber, 54),
        )
        for index, (x_factor, y_factor, color_name, alpha) in enumerate(field_specs):
            drift = math.sin(math.radians(phase * 0.45 + index * 71)) * radius * 0.04
            field_center = QPointF(
                center.x() + x_factor * radius + drift,
                center.y() + y_factor * radius - drift * 0.45,
            )
            gradient = QRadialGradient(field_center, radius * 0.58)
            color = QColor(color_name)
            color.setAlpha(alpha)
            gradient.setColorAt(0.0, color)
            color.setAlpha(round(alpha * 0.24))
            gradient.setColorAt(0.46, color)
            gradient.setColorAt(1.0, QColor(2, 6, 13, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawEllipse(field_center, radius * 0.62, radius * 0.62)

    def _paint_color_currents(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        phase: float,
    ) -> None:
        for index, color_name in enumerate(
            (COLORS.cyan, COLORS.blue, COLORS.magenta, COLORS.amber, COLORS.cyan)
        ):
            vertical = (-0.56 + index * 0.28) * radius
            sway = math.sin(math.radians(phase * 0.7 + index * 64)) * radius * 0.12
            path = QPainterPath(
                QPointF(center.x() - radius * 0.94, center.y() + vertical * 0.45)
            )
            path.cubicTo(
                QPointF(center.x() - radius * 0.42, center.y() - radius * 0.72 + sway),
                QPointF(center.x() + radius * 0.34, center.y() + radius * 0.76 - sway),
                QPointF(center.x() + radius * 0.94, center.y() - vertical * 0.38),
            )
            glow = QColor(color_name)
            glow.setAlpha(24)
            painter.setPen(QPen(glow, 6.0))
            painter.drawPath(path)
            line = QColor(color_name)
            line.setAlpha(126)
            painter.setPen(QPen(line, 1.15))
            painter.drawPath(path)

    def _paint_sphere_grid(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        phase: float,
    ) -> None:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for index in range(-4, 5):
            y = center.y() + index * radius * 0.18
            width = radius * math.sqrt(max(0.0, 1.0 - (index * 0.18) ** 2))
            color = QColor(COLORS.cyan if index % 2 == 0 else COLORS.blue)
            color.setAlpha(34)
            painter.setPen(QPen(color, 0.8))
            painter.drawEllipse(QPointF(center.x(), y), width, radius * 0.08)

        painter.save()
        painter.translate(center)
        painter.rotate(phase * 0.07)
        for angle in range(0, 180, 24):
            painter.save()
            painter.rotate(angle)
            painter.setPen(QPen(QColor(80, 232, 255, 28), 0.8))
            painter.drawEllipse(QPointF(0, 0), radius * 0.18, radius * 0.95)
            painter.restore()
        painter.restore()

    def _paint_network(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        phase: float,
    ) -> None:
        points = tuple(
            QPointF(center.x() + point.x() * radius, center.y() + point.y() * radius)
            for point in self._nodes
        )
        for edge_index, (start_index, end_index) in enumerate(self._edges):
            color = QColor(COLORS.cyan if edge_index % 3 else COLORS.magenta)
            color.setAlpha(42)
            painter.setPen(QPen(color, 0.75))
            painter.drawLine(points[start_index], points[end_index])

            if edge_index % 9 == 0:
                t = ((phase * 0.004) + edge_index * 0.071) % 1.0
                start = points[start_index]
                end = points[end_index]
                pulse = QPointF(
                    start.x() + (end.x() - start.x()) * t,
                    start.y() + (end.y() - start.y()) * t,
                )
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(80, 232, 255, 52))
                painter.drawEllipse(pulse, 5.0, 5.0)
                painter.setBrush(QColor(COLORS.cyan))
                painter.drawEllipse(pulse, 1.6, 1.6)

        painter.setPen(Qt.PenStyle.NoPen)
        for index, point in enumerate(points):
            color = QColor(COLORS.cyan if index % 4 else COLORS.magenta)
            color.setAlpha(170)
            painter.setBrush(color)
            painter.drawEllipse(point, 1.35 + (index % 3) * 0.35, 1.35 + (index % 3) * 0.35)

    def _paint_base(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        phase: float,
    ) -> None:
        base_center = QPointF(center.x(), center.y() + radius * 1.06)
        for index, color_name in enumerate(
            (COLORS.blue, COLORS.cyan, COLORS.magenta, COLORS.amber)
        ):
            width = radius * (1.32 - index * 0.17)
            rect = QRectF(
                base_center.x() - width,
                base_center.y() - 18 - index * 2,
                width * 2,
                36 + index * 4,
            )
            color = QColor(color_name)
            color.setAlpha(92 - index * 11)
            painter.setPen(QPen(color, 1.3))
            start = int((phase * (0.2 if index % 2 == 0 else -0.18) + index * 56) * 16)
            painter.drawArc(rect, start, int((118 - index * 12) * 16))

    def _paint_identity(self, painter: QPainter, center: QPointF, state: str) -> None:
        painter.setPen(QColor(COLORS.text))
        painter.setFont(QFont("Segoe UI", 21, QFont.Weight.Light))
        painter.drawText(
            QRectF(center.x() - 110, center.y() - 22, 220, 38),
            Qt.AlignmentFlag.AlignCenter,
            "FRIDAY",
        )
        painter.setPen(QColor(COLORS.text_soft))
        painter.setFont(QFont("Consolas", 8, QFont.Weight.DemiBold))
        painter.drawText(
            QRectF(center.x() - 110, center.y() + 12, 220, 26),
            Qt.AlignmentFlag.AlignCenter,
            f"LOCAL CORE  /  {state.upper()}",
        )
