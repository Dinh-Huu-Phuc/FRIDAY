from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from friday.app.neural_visual.schemas import (
    NeuralEventStatus,
    NeuralTelemetryEvent,
)
from friday.app.neural_visual.topology import (
    NEURAL_EDGES,
    NEURAL_NODES,
    NeuralEdgeDefinition,
    NeuralNodeDefinition,
    NeuralNodeId,
)


@dataclass(slots=True)
class NeuralPulse:
    event: NeuralTelemetryEvent
    progress: float = 0.0


@dataclass(slots=True)
class NeuralNodeRuntime:
    activity: float = 0.0
    incoming_count: int = 0
    outgoing_count: int = 0
    last_event: NeuralTelemetryEvent | None = None
    last_incoming: NeuralTelemetryEvent | None = None
    last_outgoing: NeuralTelemetryEvent | None = None


class NeuralNetworkVisual(QWidget):
    _STATE_COLORS: ClassVar[dict[str, QColor]] = {
        "listening": QColor("#63dff2"),
        "thinking": QColor("#f0c56e"),
        "speaking": QColor("#71efb3"),
        "sleeping": QColor("#60747d"),
        "online": QColor("#58e1e5"),
    }
    _EVENT_COLORS: ClassVar[dict[NeuralEventStatus, QColor]] = {
        NeuralEventStatus.ACTIVE: QColor("#54dce5"),
        NeuralEventStatus.SUCCESS: QColor("#70e6a7"),
        NeuralEventStatus.ERROR: QColor("#ff6578"),
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(480, 360)
        self.setMouseTracking(True)
        self._state = "online"
        self._phase = 0.0
        self._nodes = list(NEURAL_NODES)
        self._edges = list(NEURAL_EDGES)
        self._node_map = {node.id: node for node in self._nodes}
        self._edge_map = {edge.id: edge for edge in self._edges}
        self._node_runtime = {
            node.id: NeuralNodeRuntime() for node in self._nodes
        }
        self._edge_events: dict[str, NeuralTelemetryEvent] = {}
        self._pulses: list[NeuralPulse] = []
        self._hover_node_id: str | None = None
        self._hover_edge_id: str | None = None
        self._cursor_position = QPointF()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._advance)

    @property
    def state(self) -> str:
        return self._state

    @property
    def active_pulse_count(self) -> int:
        return len(self._pulses)

    def set_state(self, state: str) -> None:
        self._state = state if state in self._STATE_COLORS else "online"
        self.update()

    def ingest_event(self, event: NeuralTelemetryEvent) -> None:
        target_runtime = self._node_runtime.get(event.target_node)
        if target_runtime is None:
            return
        target_runtime.activity = 1.0
        target_runtime.last_event = event
        if event.source_node:
            target_runtime.incoming_count += 1
            target_runtime.last_incoming = event
            source_runtime = self._node_runtime.get(event.source_node)
            edge_id = f"{event.source_node}->{event.target_node}"
            if source_runtime is not None:
                source_runtime.activity = max(source_runtime.activity, 0.72)
                source_runtime.outgoing_count += 1
                source_runtime.last_event = event
                source_runtime.last_outgoing = event
            if edge_id in self._edge_map:
                self._edge_events[edge_id] = event
                self._pulses.append(NeuralPulse(event=event))
                self._pulses = self._pulses[-80:]
        self.update()

    def clear_telemetry(self) -> None:
        self._pulses.clear()
        self._edge_events.clear()
        self._node_runtime = {
            node.id: NeuralNodeRuntime() for node in self._nodes
        }
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._timer.isActive():
            self._timer.start(30)

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def mouseMoveEvent(self, event) -> None:
        self._cursor_position = event.position()
        points = self._node_points()
        node_id = self._node_at(self._cursor_position, points)
        edge_id = None if node_id else self._edge_at(self._cursor_position, points)
        changed = (
            node_id != self._hover_node_id
            or edge_id != self._hover_edge_id
        )
        self._hover_node_id = node_id
        self._hover_edge_id = edge_id
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if node_id or edge_id
            else Qt.CursorShape.ArrowCursor
        )
        if changed or node_id or edge_id:
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover_node_id = None
        self._hover_edge_id = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().leaveEvent(event)

    def _advance(self) -> None:
        state_rate = {
            "listening": 1.35,
            "thinking": 1.65,
            "speaking": 1.45,
            "sleeping": 0.25,
        }.get(self._state, 0.55)
        self._phase = (self._phase + state_rate) % 100_000
        for runtime in self._node_runtime.values():
            runtime.activity = max(0.0, runtime.activity - 0.012)
        pulse_speed = 0.024 if self._state == "sleeping" else 0.038
        for pulse in self._pulses:
            pulse.progress += pulse_speed
        self._pulses = [pulse for pulse in self._pulses if pulse.progress <= 1.12]
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#020608"))
        self._draw_grid(painter)
        points = self._node_points()
        paths = {
            edge.id: self._edge_path(edge, points, self._network_bounds().height())
            for edge in self._edges
        }
        self._draw_edges(painter, paths)
        self._draw_pulses(painter, paths)
        self._draw_nodes(painter, points)
        self._draw_inspector(painter)

    def _network_bounds(self) -> QRectF:
        return QRectF(
            28,
            24,
            max(1, self.width() - 56),
            max(1, self.height() - 54),
        )

    def _node_points(self) -> dict[str, QPointF]:
        bounds = self._network_bounds()
        return {
            node.id: QPointF(
                bounds.left() + node.x * bounds.width(),
                bounds.top() + node.y * bounds.height(),
            )
            for node in self._nodes
        }

    def _draw_grid(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor(69, 140, 151, 18), 1))
        step = 38
        for x in range(0, self.width(), step):
            for y in range(0, self.height(), step):
                painter.drawPoint(x, y)

    @staticmethod
    def _edge_path(
        edge: NeuralEdgeDefinition,
        points: dict[str, QPointF],
        height: float,
    ) -> QPainterPath:
        start = points[edge.source]
        end = points[edge.target]
        distance = end.x() - start.x()
        bend = edge.bend * height
        path = QPainterPath(start)
        path.cubicTo(
            QPointF(start.x() + distance * 0.42, start.y() + bend),
            QPointF(end.x() - distance * 0.42, end.y() - bend),
            end,
        )
        return path

    def _draw_edges(
        self,
        painter: QPainter,
        paths: dict[str, QPainterPath],
    ) -> None:
        hovered_node = self._hover_node_id
        hovered_edge = self._hover_edge_id
        for edge in self._edges:
            related = hovered_node in {edge.source, edge.target}
            if hovered_node:
                alpha = 112 if related else 9
                width = 1.7 if related else 0.8
            elif hovered_edge:
                alpha = 130 if edge.id == hovered_edge else 12
                width = 1.9 if edge.id == hovered_edge else 0.8
            elif edge.id in self._edge_events:
                alpha = 64
                width = 1.25
            else:
                alpha = 24
                width = 0.9
            color = QColor("#4bcbd5")
            color.setAlpha(alpha)
            painter.setPen(QPen(color, width))
            painter.drawPath(paths[edge.id])

    def _draw_pulses(
        self,
        painter: QPainter,
        paths: dict[str, QPainterPath],
    ) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        for pulse in self._pulses:
            event = pulse.event
            edge_id = f"{event.source_node}->{event.target_node}"
            path = paths.get(edge_id)
            if path is None:
                continue
            color = self._EVENT_COLORS[event.status]
            progress = min(1.0, pulse.progress)
            for tail_index in range(6, -1, -1):
                tail_progress = progress - tail_index * 0.018
                if tail_progress < 0:
                    continue
                point = path.pointAtPercent(tail_progress)
                intensity = (7 - tail_index) / 7
                glow = QColor(
                    color.red(),
                    color.green(),
                    color.blue(),
                    round(24 + 135 * intensity),
                )
                painter.setBrush(glow)
                radius = 1.0 + 2.5 * intensity
                painter.drawEllipse(point, radius, radius)
            head = path.pointAtPercent(progress)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 42))
            painter.drawEllipse(head, 9.0, 9.0)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 180))
            painter.drawEllipse(head, 4.3, 4.3)
            painter.setBrush(QColor("#efffff"))
            painter.drawEllipse(head, 1.6, 1.6)

    def _draw_nodes(
        self,
        painter: QPainter,
        points: dict[str, QPointF],
    ) -> None:
        base_color = self._STATE_COLORS[self._state]
        for index, node in enumerate(self._nodes):
            point = points[node.id]
            runtime = self._node_runtime[node.id]
            idle_breath = 0.5 + 0.5 * math.sin(
                math.radians(self._phase * 2.2 + index * 41)
            )
            activity = runtime.activity
            event_color = (
                self._EVENT_COLORS[runtime.last_event.status]
                if runtime.last_event and activity > 0.01
                else base_color
            )
            hovered = node.id == self._hover_node_id
            radius = node.radius * (
                1.0
                + idle_breath * 0.05
                + activity * 0.36
                + (0.28 if hovered else 0.0)
            )
            glow_radius = radius * (4.2 if activity > 0.05 or hovered else 2.5)
            glow = QRadialGradient(point, glow_radius)
            glow.setColorAt(
                0.0,
                QColor(
                    event_color.red(),
                    event_color.green(),
                    event_color.blue(),
                    185 if hovered else round(65 + activity * 105),
                ),
            )
            glow.setColorAt(1.0, QColor(event_color.red(), event_color.green(), event_color.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(point, glow_radius, glow_radius)
            painter.setPen(QPen(QColor(event_color.red(), event_color.green(), event_color.blue(), 225), 1.2))
            painter.setBrush(
                QColor(
                    event_color.red(),
                    event_color.green(),
                    event_color.blue(),
                    round(78 + idle_breath * 55 + activity * 105),
                )
            )
            painter.drawEllipse(point, radius, radius)

            if node.id == NeuralNodeId.INTENT_ROUTER:
                painter.setPen(QColor("#f4ffff"))
                painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                painter.drawText(
                    QRectF(point.x() - radius, point.y() - radius, radius * 2, radius * 2),
                    Qt.AlignmentFlag.AlignCenter,
                    "F",
                )

            label_color = QColor("#d4f5f6") if hovered else QColor("#7ca8ad")
            painter.setPen(label_color)
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
            label_bounds = QRectF(point.x() - 42, point.y() + radius + 4, 84, 14)
            painter.drawText(label_bounds, Qt.AlignmentFlag.AlignHCenter, node.label)

    def _node_at(
        self,
        position: QPointF,
        points: dict[str, QPointF] | None = None,
    ) -> str | None:
        resolved_points = points or self._node_points()
        for node in reversed(self._nodes):
            point = resolved_points[node.id]
            hit_radius = max(11.0, node.radius * 2.2)
            if math.hypot(position.x() - point.x(), position.y() - point.y()) <= hit_radius:
                return node.id
        return None

    def _edge_at(
        self,
        position: QPointF,
        points: dict[str, QPointF] | None = None,
    ) -> str | None:
        resolved_points = points or self._node_points()
        stroker = QPainterPathStroker()
        stroker.setWidth(10.0)
        for edge in self._edges:
            path = self._edge_path(edge, resolved_points, self._network_bounds().height())
            if stroker.createStroke(path).contains(position):
                return edge.id
        return None

    def _draw_inspector(self, painter: QPainter) -> None:
        if self._hover_node_id:
            self._draw_node_inspector(painter, self._node_map[self._hover_node_id])
        elif self._hover_edge_id:
            self._draw_edge_inspector(painter, self._edge_map[self._hover_edge_id])

    def _inspector_rect(self, preferred_height: float) -> QRectF:
        width = min(310.0, max(235.0, self.width() * 0.42))
        x = self._cursor_position.x() + 16
        y = self._cursor_position.y() + 14
        if x + width > self.width() - 10:
            x = self._cursor_position.x() - width - 16
        if y + preferred_height > self.height() - 10:
            y = self._cursor_position.y() - preferred_height - 14
        return QRectF(max(10.0, x), max(10.0, y), width, preferred_height)

    def _draw_panel(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(QColor(71, 205, 215, 145), 1.0))
        painter.setBrush(QColor(4, 13, 17, 241))
        painter.drawRoundedRect(rect, 5, 5)

    @staticmethod
    def _elide(painter: QPainter, text: str, width: int) -> str:
        return QFontMetrics(painter.font()).elidedText(
            text or "No data yet",
            Qt.TextElideMode.ElideRight,
            width,
        )

    def _draw_node_inspector(
        self,
        painter: QPainter,
        node: NeuralNodeDefinition,
    ) -> None:
        rect = self._inspector_rect(150)
        self._draw_panel(painter, rect)
        runtime = self._node_runtime[node.id]
        event = runtime.last_event
        status = event.status.value.upper() if event else "IDLE"
        status_color = self._EVENT_COLORS[event.status] if event else QColor("#789398")
        left = rect.left() + 13
        width = round(rect.width() - 26)

        painter.setPen(QColor("#e9ffff"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(QPointF(left, rect.top() + 20), node.label)
        painter.setPen(status_color)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
        painter.drawText(QPointF(rect.right() - 62, rect.top() + 20), status)

        painter.setPen(QColor("#8eb5b9"))
        painter.setFont(QFont("Segoe UI", 7))
        description = self._elide(painter, node.description, width)
        painter.drawText(QPointF(left, rect.top() + 39), description)
        summary = self._elide(painter, event.summary if event else "", width)
        painter.setPen(QColor("#d2f0f1"))
        painter.drawText(QPointF(left, rect.top() + 63), f"DATA  {summary}")

        incoming = runtime.last_incoming
        outgoing = runtime.last_outgoing
        incoming_label = (
            self._node_map[incoming.source_node].label
            if incoming and incoming.source_node in self._node_map
            else "none"
        )
        outgoing_label = (
            self._node_map[outgoing.target_node].label
            if outgoing and outgoing.target_node in self._node_map
            else "none"
        )
        painter.setPen(QColor("#75a0a5"))
        painter.drawText(
            QPointF(left, rect.top() + 87),
            self._elide(
                painter,
                f"IN  {incoming_label}  /  {runtime.incoming_count} transfers",
                width,
            ),
        )
        painter.drawText(
            QPointF(left, rect.top() + 106),
            self._elide(
                painter,
                f"OUT  {outgoing_label}  /  {runtime.outgoing_count} transfers",
                width,
            ),
        )
        trace = event.trace_id[:12] if event else "-"
        latency = f"{event.duration_ms:.0f} ms" if event and event.duration_ms is not None else "live"
        painter.setPen(QColor("#587a7e"))
        painter.drawText(
            QPointF(left, rect.top() + 130),
            self._elide(painter, f"TRACE  {trace}    LATENCY  {latency}", width),
        )

    def _draw_edge_inspector(
        self,
        painter: QPainter,
        edge: NeuralEdgeDefinition,
    ) -> None:
        rect = self._inspector_rect(112)
        self._draw_panel(painter, rect)
        event = self._edge_events.get(edge.id)
        source = self._node_map[edge.source].label
        target = self._node_map[edge.target].label
        left = rect.left() + 13
        width = round(rect.width() - 26)
        painter.setPen(QColor("#e9ffff"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(QPointF(left, rect.top() + 21), f"{source}  >  {target}")
        painter.setFont(QFont("Segoe UI", 7))
        painter.setPen(QColor("#d2f0f1"))
        summary = self._elide(painter, event.summary if event else "", width)
        painter.drawText(QPointF(left, rect.top() + 48), f"DATA  {summary}")
        painter.setPen(QColor("#75a0a5"))
        kind = event.event_type if event else "No transfer recorded"
        painter.drawText(
            QPointF(left, rect.top() + 70),
            self._elide(painter, f"EVENT  {kind}", width),
        )
        painter.setPen(QColor("#587a7e"))
        status = event.status.value.upper() if event else "IDLE"
        trace = event.trace_id[:12] if event else "-"
        painter.drawText(
            QPointF(left, rect.top() + 92),
            self._elide(painter, f"STATUS  {status}    TRACE  {trace}", width),
        )
