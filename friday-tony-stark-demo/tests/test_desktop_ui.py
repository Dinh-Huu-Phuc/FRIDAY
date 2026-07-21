from __future__ import annotations

import os
import struct
import wave
from io import BytesIO

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PySide6.QtCore import QEventLoop, QThreadPool, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QTextBrowser

from friday.src.UI.routes import mount_web_ui_static
from friday.src.UI.static.desktop_ui.services.audio import (
    VoiceActivitySegmenter,
    SpeechPlayer,
    pcm16_rms,
    pcm_to_wav,
)
from friday.src.UI.static.desktop_ui.widgets.core_visual import CoreVisual
from friday.src.UI.static.desktop_ui.widgets.message_bubble import MessageBubble


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
    assert player._audio_path == ""
    pool.waitForDone(1_000)


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
    image = visual.grab().toImage()

    assert not image.isNull()
    assert image.width() == 420
    assert image.height() == 420


def test_native_python_sources_are_not_exposed_as_static_files() -> None:
    app = FastAPI()
    mount_web_ui_static(app)
    client = TestClient(app)

    assert client.get("/ui/static/Core_UI/styles.css").status_code == 200
    assert client.get("/ui/static/desktop_ui/window.py").status_code == 404
