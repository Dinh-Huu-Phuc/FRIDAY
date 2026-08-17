from __future__ import annotations

import os
import struct
import wave
from io import BytesIO
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PySide6.QtCore import QEventLoop, QSettings, QThreadPool, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QTextBrowser

from friday.app.neural_visual import (
    NeuralEventStatus,
    NeuralNodeId,
    NeuralTelemetryEvent,
)
from friday.src.UI.routes import mount_web_ui_static
from friday.src.UI.static.desktop_ui.services.audio import (
    SpeechPlayer,
    VoiceActivitySegmenter,
    pcm16_rms,
    pcm_to_wav,
)
import friday.src.UI.static.desktop_ui.widgets.settings_panel as settings_module
from friday.src.UI.static.desktop_ui.widgets.core_visual import CoreVisual
from friday.src.UI.static.desktop_ui.widgets.message_bubble import MessageBubble
from friday.src.UI.static.desktop_ui.widgets.neural_network_visual import (
    NeuralNetworkVisual,
)
from friday.src.UI.static.desktop_ui.widgets.system_status_panel import (
    SystemStatusPanel,
)
from friday.src.UI.static.desktop_ui.window import DesktopWindow


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_pcm_to_wav_builds_valid_mono_audio() -> None:
    payload = pcm_to_wav(b"\x00\x00" * 320, sample_rate=16_000)

    with wave.open(BytesIO(payload), "rb") as audio:
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
        assert audio.getframerate() == 16_000
        assert audio.getnframes() == 320


def test_voice_activity_segmenter_closes_a_spoken_turn_after_silence() -> None:
    segmenter = VoiceActivitySegmenter(
        sample_rate=1_000,
        threshold=500,
        silence_ms=300,
        pre_roll_ms=200,
        min_voice_ms=200,
    )
    silence = struct.pack("<100h", *([0] * 100))
    voice = struct.pack("<100h", *([2_000] * 100))

    segmenter.process(silence)
    segmenter.process(silence)
    started, utterance = segmenter.process(voice)
    assert started
    assert utterance is None
    segmenter.process(voice)
    segmenter.process(voice)
    segmenter.process(silence)
    segmenter.process(silence)
    _, utterance = segmenter.process(silence)

    assert utterance is not None
    assert pcm16_rms(utterance) > 500
    assert not segmenter.speaking


def test_voice_activity_segmenter_ignores_short_noise() -> None:
    segmenter = VoiceActivitySegmenter(
        sample_rate=1_000,
        threshold=500,
        silence_ms=200,
        min_voice_ms=250,
    )
    silence = struct.pack("<100h", *([0] * 100))
    short_noise = struct.pack("<100h", *([1_500] * 100))

    segmenter.process(short_noise)
    segmenter.process(silence)
    _, utterance = segmenter.process(silence)

    assert utterance is None
    assert not segmenter.speaking


def test_speech_player_watchdog_releases_the_microphone_gate() -> None:
    _app()
    pool = QThreadPool()
    player = SpeechPlayer(pool)
    states: list[bool] = []
    player.speaking_changed.connect(states.append)
    player.speaking_changed.emit(True)
    player._play_bytes(pcm_to_wav(b"\x00\x00" * 1_600, sample_rate=16_000))

    loop = QEventLoop()
    QTimer.singleShot(2_000, loop.quit)
    loop.exec()

    assert states[0] is True
    assert states[-1] is False
    assert player._audio_sink is None
    assert player._audio_buffer is None
    pool.waitForDone(1_000)


def test_speech_player_decodes_the_entire_wav_payload() -> None:
    _app()
    pcm = b"\x01\x00" * 32_000
    payload = pcm_to_wav(pcm, sample_rate=16_000)

    decoded, audio_format, duration_ms = SpeechPlayer._decode_wav(payload)

    assert decoded == pcm
    assert audio_format.sampleRate() == 16_000
    assert audio_format.channelCount() == 1
    assert duration_ms == 2_000


def test_native_message_can_render_markdown_and_copy() -> None:
    _app()
    bubble = MessageBubble(
        {
            "role": "assistant",
            "content": "**Result:** $E = mc^2$",
            "timestamp": "2026-07-20T12:00:00+00:00",
        }
    )
    body = bubble.findChild(QTextBrowser)

    assert body is not None
    assert "Result:" in body.toPlainText()
    bubble._copy()
    assert QGuiApplication.clipboard().text() == "**Result:** $E = mc^2$"


def test_core_visual_renders_offscreen() -> None:
    _app()
    visual = CoreVisual()
    visual.resize(420, 420)
    visual.set_state("thinking")
    visual.set_audio_level(0.82)
    image = visual.grab().toImage()

    assert not image.isNull()
    assert image.width() == 420
    assert image.height() == 420


def test_visual_settings_keep_orb_video_and_neural_modes(tmp_path, monkeypatch) -> None:
    _app()
    monkeypatch.setattr(
        settings_module,
        "get_auto_sleep_settings",
        lambda: SimpleNamespace(minutes=15),
    )
    settings = QSettings(str(tmp_path / "desktop-ui.ini"), QSettings.Format.IniFormat)
    panel = settings_module.SettingsPanel(settings)

    panel.select_visual("video")
    assert settings.value("appearance/visual") == "video"
    panel.select_visual("neural")
    assert settings.value("appearance/visual") == "neural"
    panel.select_visual("orb")
    assert settings.value("appearance/visual") == "orb"


def test_system_status_panel_tracks_visual_runtime_state() -> None:
    _app()
    panel = SystemStatusPanel()

    panel.set_core_state("speaking")
    assert panel.runtime_state.text() == "SPEAKING"
    panel.set_core_state("sleeping")
    assert panel.runtime_state.text() == "SLEEPING"


def test_neural_network_visual_renders_nodes_edges_and_motion() -> None:
    _app()
    visual = NeuralNetworkVisual()
    visual.resize(640, 420)
    visual.set_state("thinking")
    first = visual.grab().toImage()
    assert visual.active_pulse_count == 0
    visual.ingest_event(
        NeuralTelemetryEvent(
            trace_id="desktop-render-test",
            source_node=NeuralNodeId.TEXT_INPUT,
            target_node=NeuralNodeId.INTENT_ROUTER,
            event_type="intent.routing.started",
            summary="Open the neural network",
            status=NeuralEventStatus.ACTIVE,
        )
    )
    for _ in range(12):
        visual._advance()
    second = visual.grab().toImage()

    assert len(visual._nodes) >= 12
    assert len(visual._edges) >= 20
    assert visual.active_pulse_count == 1
    intent_point = visual._node_points()[NeuralNodeId.INTENT_ROUTER]
    assert visual._node_at(intent_point) == NeuralNodeId.INTENT_ROUTER
    assert visual.state == "thinking"
    assert not first.isNull()
    assert not second.isNull()
    assert first != second


def test_send_message_ignores_qt_clicked_boolean_metadata() -> None:
    class InputStub:
        def __init__(self) -> None:
            self.read_count = 0

        def toPlainText(self) -> str:
            self.read_count += 1
            return "FRIDAY open code map"

    input_stub = InputStub()
    window_stub = type("WindowStub", (), {"input": input_stub, "_busy": True})()

    DesktopWindow.send_message(window_stub, False)

    assert input_stub.read_count == 1


def test_native_python_sources_are_not_exposed_as_static_files() -> None:
    app = FastAPI()
    mount_web_ui_static(app)
    client = TestClient(app)

    assert client.get("/ui/static/Core_UI/styles.css").status_code == 200
    assert client.get("/ui/static/desktop_ui/window.py").status_code == 404
    assert client.get("/ui/static/code_map_ui/window.py").status_code == 404
