from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path(__file__).resolve().parent / "assets" / "friday_model_parameters"
WIDTH = 1600
HEIGHT = 900

BG = QColor("#02080b")
PANEL = QColor("#071217")
PANEL_2 = QColor("#0a1920")
GRID = QColor(83, 221, 229, 18)
TEXT = QColor("#e9fbff")
MUTED = QColor("#8fb1ba")
AQUA = QColor("#58e1e5")
GREEN = QColor("#71efb3")
GOLD = QColor("#f0c56e")
RED = QColor("#ff6d75")
BLUE = QColor("#76aef5")


def font(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    return QFont("Segoe UI", size, weight)


def canvas() -> tuple[QImage, QPainter]:
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32)
    image.fill(BG)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    painter.setPen(QPen(GRID, 1))
    for x in range(0, WIDTH, 40):
        painter.drawLine(x, 0, x, HEIGHT)
    for y in range(0, HEIGHT, 40):
        painter.drawLine(0, y, WIDTH, y)
    return image, painter


def title(painter: QPainter, heading: str, subtitle: str) -> None:
    painter.setPen(TEXT)
    painter.setFont(font(29, QFont.Weight.Bold))
    painter.drawText(QRectF(70, 46, 1460, 48), heading)
    painter.setPen(MUTED)
    painter.setFont(font(13))
    painter.drawText(QRectF(72, 102, 1450, 28), subtitle)
    painter.setPen(QPen(AQUA, 2))
    painter.drawLine(72, 140, 1528, 140)


def panel(painter: QPainter, rect: QRectF, accent: QColor = AQUA) -> None:
    painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 95), 1.3))
    painter.setBrush(PANEL)
    painter.drawRoundedRect(rect, 6, 6)


def pill(painter: QPainter, rect: QRectF, label: str, color: QColor) -> None:
    painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 150), 1))
    painter.setBrush(QColor(color.red(), color.green(), color.blue(), 24))
    painter.drawRoundedRect(rect, 5, 5)
    painter.setPen(color)
    painter.setFont(font(11, QFont.Weight.DemiBold))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)


def connector(
    painter: QPainter,
    start: QPointF,
    end: QPointF,
    color: QColor,
    dashed: bool = False,
) -> None:
    path = QPainterPath(start)
    mid_x = (start.x() + end.x()) / 2
    path.cubicTo(QPointF(mid_x, start.y()), QPointF(mid_x, end.y()), end)
    style = Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine
    painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 150), 2, style))
    painter.drawPath(path)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(end, 4.5, 4.5)


def draw_runtime_architecture() -> None:
    image, painter = canvas()
    title(
        painter,
        "FRIDAY MODEL RUNTIME MAP",
        "Neural models are distributed across local inference and remote provider APIs.",
    )

    left = QRectF(70, 190, 430, 610)
    center = QRectF(570, 300, 460, 390)
    right = QRectF(1100, 190, 430, 610)
    panel(painter, left, AQUA)
    panel(painter, center, GREEN)
    panel(painter, right, GOLD)

    painter.setFont(font(16, QFont.Weight.Bold))
    painter.setPen(AQUA)
    painter.drawText(QRectF(95, 215, 380, 35), "LOCAL / USER MACHINE")
    painter.setPen(GREEN)
    painter.drawText(QRectF(595, 325, 410, 35), "FRIDAY ORCHESTRATION")
    painter.setPen(GOLD)
    painter.drawText(QRectF(1125, 215, 380, 35), "REMOTE / PROVIDER APIS")

    local_items = [
        ("Ollama Gemma 3", "4.3B | vision + completion", AQUA),
        ("Silero VAD", "~260K | speech activity", GREEN),
        ("Hash embeddings", "algorithmic | 0 learned params", BLUE),
        ("Neural UI visual", "animation | 0 learned params", MUTED),
    ]
    y = 280
    for name, detail, color in local_items:
        rect = QRectF(95, y, 380, 92)
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 85), 1))
        painter.setBrush(PANEL_2)
        painter.drawRoundedRect(rect, 5, 5)
        painter.setPen(TEXT)
        painter.setFont(font(14, QFont.Weight.DemiBold))
        painter.drawText(QRectF(116, y + 15, 330, 28), name)
        painter.setPen(MUTED)
        painter.setFont(font(11))
        painter.drawText(QRectF(116, y + 49, 330, 24), detail)
        y += 112

    painter.setPen(TEXT)
    painter.setFont(font(24, QFont.Weight.Bold))
    painter.drawText(QRectF(620, 405, 360, 45), Qt.AlignmentFlag.AlignCenter, "FRIDAY")
    painter.setPen(MUTED)
    painter.setFont(font(12))
    painter.drawText(
        QRectF(620, 458, 360, 72),
        Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
        "Intent routing, tools, memory, browser automation, UI and response delivery",
    )
    pill(painter, QRectF(650, 565, 300, 42), "SOFTWARE LAYER: NOT MODEL WEIGHTS", GREEN)

    remote_items = [
        ("Gemini 2.5 Flash", "main LLM | size undisclosed", GOLD),
        ("Sarvam Saaras / Bulbul", "STT + TTS | size undisclosed", RED),
        ("Groq Llama 3.1 8B", "STT refiner | nominal 8B", BLUE),
        ("OpenAI tts-1", "desktop TTS | size undisclosed", GREEN),
    ]
    y = 280
    for name, detail, color in remote_items:
        rect = QRectF(1125, y, 380, 92)
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 85), 1))
        painter.setBrush(PANEL_2)
        painter.drawRoundedRect(rect, 5, 5)
        painter.setPen(TEXT)
        painter.setFont(font(14, QFont.Weight.DemiBold))
        painter.drawText(QRectF(1146, y + 15, 330, 28), name)
        painter.setPen(MUTED)
        painter.setFont(font(11))
        painter.drawText(QRectF(1146, y + 49, 330, 24), detail)
        y += 112

    connector(painter, QPointF(500, 430), QPointF(570, 430), AQUA)
    connector(painter, QPointF(500, 565), QPointF(570, 565), AQUA)
    connector(painter, QPointF(1030, 430), QPointF(1100, 430), GOLD, dashed=True)
    connector(painter, QPointF(1030, 565), QPointF(1100, 565), GOLD, dashed=True)

    painter.setPen(MUTED)
    painter.setFont(font(10))
    painter.drawText(
        QRectF(70, 832, 1460, 30),
        Qt.AlignmentFlag.AlignCenter,
        "Dashed links cross the network boundary. Remote weights are not stored in the FRIDAY repository.",
    )
    painter.end()
    image.save(str(OUTPUT_DIR / "01_runtime_architecture.png"))


def draw_parameter_scope() -> None:
    image, painter = canvas()
    title(
        painter,
        "VERIFIABLE PARAMETER SCOPE",
        "A disclosed-only comparison. It is not the parameter count of one combined model.",
    )

    chart = QRectF(90, 190, 990, 570)
    side = QRectF(1120, 190, 390, 570)
    panel(painter, chart, AQUA)
    panel(painter, side, GOLD)

    painter.setPen(MUTED)
    painter.setFont(font(11))
    x0 = 320
    chart_width = 680
    for tick in range(0, 9, 2):
        x = x0 + chart_width * tick / 8
        painter.setPen(QPen(QColor(120, 190, 198, 35), 1))
        painter.drawLine(round(x), 250, round(x), 650)
        painter.setPen(MUTED)
        painter.drawText(QRectF(x - 30, 665, 60, 25), Qt.AlignmentFlag.AlignCenter, f"{tick}B")

    rows = [
        ("Gemma 3 local", 4.3, AQUA, "4.3B"),
        ("Llama 3.1 remote", 8.0, BLUE, "8.0B"),
    ]
    y = 310
    for label, value, color, value_label in rows:
        painter.setPen(TEXT)
        painter.setFont(font(14, QFont.Weight.DemiBold))
        painter.drawText(QRectF(120, y, 180, 38), Qt.AlignmentFlag.AlignVCenter, label)
        rect = QRectF(x0, y, chart_width * value / 8, 38)
        gradient = QLinearGradient(rect.left(), 0, rect.right(), 0)
        gradient.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), 75))
        gradient.setColorAt(1.0, color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(TEXT)
        painter.setFont(font(13, QFont.Weight.Bold))
        painter.drawText(QRectF(rect.right() - 90, y, 80, 38), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, value_label)
        y += 130

    vad_rect = QRectF(120, 570, 880, 64)
    painter.setPen(QPen(QColor(GREEN.red(), GREEN.green(), GREEN.blue(), 95), 1))
    painter.setBrush(QColor(GREEN.red(), GREEN.green(), GREEN.blue(), 18))
    painter.drawRoundedRect(vad_rect, 5, 5)
    painter.setPen(GREEN)
    painter.setFont(font(14, QFont.Weight.DemiBold))
    painter.drawText(QRectF(142, 580, 270, 40), Qt.AlignmentFlag.AlignVCenter, "Silero VAD: ~260K")
    painter.setPen(MUTED)
    painter.setFont(font(11))
    painter.drawText(
        QRectF(420, 580, 550, 40),
        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        "0.00026B; too small to appear on the 0-8B scale",
    )

    painter.setPen(GOLD)
    painter.setFont(font(16, QFont.Weight.Bold))
    painter.drawText(QRectF(1150, 225, 330, 34), "REPORTING TOTALS")
    blocks = [
        ("LOCAL NEURAL WEIGHTS", "~4.30B", AQUA),
        ("KNOWN-SIZE PARTIAL SUM", "~12.30B", BLUE),
        ("TRUE END-TO-END TOTAL", "UNKNOWN", GOLD),
    ]
    y = 292
    for label, value, color in blocks:
        painter.setPen(MUTED)
        painter.setFont(font(10, QFont.Weight.DemiBold))
        painter.drawText(QRectF(1152, y, 326, 24), label)
        painter.setPen(color)
        painter.setFont(font(29, QFont.Weight.Bold))
        painter.drawText(QRectF(1150, y + 25, 330, 48), value)
        y += 120

    painter.setPen(MUTED)
    painter.setFont(font(10))
    painter.drawText(
        QRectF(1148, 655, 334, 76),
        Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
        "Gemini, Sarvam and OpenAI service parameter counts are not verified in the official product documentation reviewed.",
    )
    painter.setPen(TEXT)
    painter.setFont(font(11, QFont.Weight.DemiBold))
    painter.drawText(
        QRectF(90, 810, 1420, 32),
        Qt.AlignmentFlag.AlignCenter,
        "Quantization changes storage and arithmetic precision, not the number of model parameters.",
    )
    painter.end()
    image.save(str(OUTPUT_DIR / "02_parameter_scope.png"))


def draw_ollama_spec() -> None:
    image, painter = canvas()
    title(
        painter,
        "LOCAL OLLAMA SNAPSHOT: GEMMA3:4B",
        "Values captured from `ollama list` and `ollama show gemma3:4b` on this machine.",
    )
    main = QRectF(70, 190, 1460, 600)
    panel(painter, main, AQUA)

    painter.setPen(TEXT)
    painter.setFont(font(42, QFont.Weight.Bold))
    painter.drawText(QRectF(120, 240, 520, 70), "GEMMA 3")
    painter.setPen(AQUA)
    painter.setFont(font(70, QFont.Weight.Bold))
    painter.drawText(QRectF(115, 325, 560, 105), "4.3B")
    painter.setPen(MUTED)
    painter.setFont(font(15))
    painter.drawText(QRectF(125, 443, 480, 34), "parameters reported by the local Ollama manifest")
    pill(painter, QRectF(125, 520, 210, 48), "LOCAL INFERENCE", AQUA)
    pill(painter, QRectF(355, 520, 210, 48), "VISION + TEXT", GREEN)

    specs = [
        ("QUANTIZATION", "Q4_K_M", GOLD),
        ("MODEL STORAGE", "3.3 GB", AQUA),
        ("CONTEXT LENGTH", "131,072", BLUE),
        ("EMBEDDING LENGTH", "2,560", GREEN),
    ]
    positions = [(700, 245), (1090, 245), (700, 470), (1090, 470)]
    for (label, value, color), (x, y) in zip(specs, positions, strict=True):
        rect = QRectF(x, y, 340, 165)
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 95), 1.2))
        painter.setBrush(PANEL_2)
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(MUTED)
        painter.setFont(font(11, QFont.Weight.DemiBold))
        painter.drawText(QRectF(x + 24, y + 26, 292, 25), label)
        painter.setPen(color)
        painter.setFont(font(28, QFont.Weight.Bold))
        painter.drawText(QRectF(x + 24, y + 70, 292, 55), value)

    painter.setPen(MUTED)
    painter.setFont(font(11))
    painter.drawText(
        QRectF(125, 630, 500, 84),
        Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
        "The 4B tag is a family label. The installed manifest reports 4.3B. Q4_K_M reduces memory use but does not turn 4.3B parameters into a smaller model count.",
    )
    painter.setPen(MUTED)
    painter.setFont(font(10))
    painter.drawText(
        QRectF(70, 825, 1460, 30),
        Qt.AlignmentFlag.AlignCenter,
        "Snapshot date: 2026-07-22 | Ollama model ID: a2af6cc3eb7f",
    )
    painter.end()
    image.save(str(OUTPUT_DIR / "03_ollama_gemma3_spec.png"))


def draw_neural_visual(app: QApplication) -> None:
    sys.path.insert(0, str(PROJECT_ROOT))
    from friday.src.UI.static.desktop_ui.widgets.neural_network_visual import (
        NeuralNetworkVisual,
    )

    widget = NeuralNetworkVisual()
    widget.resize(WIDTH, HEIGHT)
    widget.set_state("online")
    for _ in range(180):
        widget._advance()
    widget.show()
    app.processEvents()
    image = QImage(widget.size(), QImage.Format.Format_ARGB32)
    image.fill(BG)
    widget.render(image)
    image.save(str(OUTPUT_DIR / "04_neural_ui_visualization.png"))
    widget.close()


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    for font_path in (
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf"),
    ):
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))
    draw_runtime_architecture()
    draw_parameter_scope()
    draw_ollama_spec()
    draw_neural_visual(app)
    print(f"Generated report figures in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
