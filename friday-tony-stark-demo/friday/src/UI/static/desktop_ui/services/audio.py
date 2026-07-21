from __future__ import annotations

import asyncio
import io
import math
import os
import tempfile
import wave
from array import array
from collections import deque
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, QThreadPool, QTimer, QUrl, Signal
from PySide6.QtMultimedia import (
    QAudioFormat,
    QAudioOutput,
    QAudioSource,
    QMediaDevices,
    QMediaPlayer,
)

from friday.app.agent_console.tts_service import synthesize_console_speech
from friday.src.UI.static.desktop_ui.controllers.tasks import FunctionTask
from friday.src.services.agent.stt_service import transcribe_core_audio


def pcm_to_wav(pcm: bytes, *, sample_rate: int, channels: int = 1) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)
    return output.getvalue()


class SpeechPlayer(QObject):
    error = Signal(str)
    speaking_changed = Signal(bool)

    def __init__(self, thread_pool: QThreadPool, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread_pool = thread_pool
        self._queue: deque[str] = deque()
        self._loading = False
        self._enabled = True
        self._audio_output = QAudioOutput(self)
        self._audio_output.setVolume(1.0)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio_output)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.errorOccurred.connect(lambda _error, message: self._fail(message))
        self._audio_path = ""
        self._playback_token = 0
        self._finishing = False

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self._queue.clear()
            self._clear_playback()
            self.speaking_changed.emit(False)

    def enqueue(self, text: str) -> None:
        normalized = text.strip()
        if not self._enabled or not normalized:
            return
        self._queue.append(normalized)
        self._start_next()

    def _start_next(self) -> None:
        if self._loading or self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return
        if not self._queue:
            self.speaking_changed.emit(False)
            return
        text = self._queue.popleft()
        self._loading = True
        self.speaking_changed.emit(True)
        task = FunctionTask(lambda: asyncio.run(synthesize_console_speech(text)))
        task.signals.completed.connect(self._play_bytes)
        task.signals.failed.connect(self._fail)
        self._thread_pool.start(task)

    def _play_bytes(self, audio: object) -> None:
        self._loading = False
        if not self._enabled:
            self.speaking_changed.emit(False)
            return
        payload = bytes(audio)
        self._clear_playback()
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix="friday_tts_",
            suffix=".wav",
            delete=False,
        ) as audio_file:
            audio_file.write(payload)
            self._audio_path = audio_file.name
        duration_ms = self._wav_duration_ms(payload)
        self._playback_token += 1
        token = self._playback_token
        self._player.setSource(QUrl.fromLocalFile(self._audio_path))
        self._player.play()
        QTimer.singleShot(
            max(1_500, duration_ms + 1_500),
            lambda: self._finish_playback(token),
        )

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._finish_playback(self._playback_token)

    def _fail(self, message: str) -> None:
        self._loading = False
        self._clear_playback()
        self.error.emit(message or "Voice playback failed.")
        self._start_next()

    def _finish_playback(self, token: int) -> None:
        if token != self._playback_token or self._finishing:
            return
        self._finishing = True
        try:
            self._clear_playback()
        finally:
            self._finishing = False
        self._start_next()

    def _clear_playback(self) -> None:
        self._playback_token += 1
        self._player.stop()
        self._player.setSource(QUrl())
        path = self._audio_path
        self._audio_path = ""
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass

    @staticmethod
    def _wav_duration_ms(payload: bytes) -> int:
        try:
            with wave.open(io.BytesIO(payload), "rb") as wav_file:
                return round(wav_file.getnframes() * 1000 / wav_file.getframerate())
        except (wave.Error, ZeroDivisionError):
            return 10_000


def pcm16_rms(pcm: bytes) -> int:
    usable = len(pcm) - (len(pcm) % 2)
    if usable <= 0:
        return 0
    samples = array("h")
    samples.frombytes(pcm[:usable])
    return math.isqrt(sum(sample * sample for sample in samples) // len(samples))


@dataclass
class VoiceActivitySegmenter:
    sample_rate: int
    channels: int = 1
    threshold: int = 250
    silence_ms: float = 850.0
    pre_roll_ms: float = 280.0
    min_voice_ms: float = 240.0
    max_utterance_ms: float = 15_000.0
    _pre_roll: deque[bytes] = field(default_factory=deque, init=False)
    _pre_roll_bytes: int = field(default=0, init=False)
    _utterance: bytearray = field(default_factory=bytearray, init=False)
    _speaking: bool = field(default=False, init=False)
    _silence_seen_ms: float = field(default=0.0, init=False)
    _voice_seen_ms: float = field(default=0.0, init=False)
    _noise_floor: float = field(default=100.0, init=False)

    @property
    def speaking(self) -> bool:
        return self._speaking

    def reset(self) -> None:
        self._pre_roll.clear()
        self._pre_roll_bytes = 0
        self._utterance.clear()
        self._speaking = False
        self._silence_seen_ms = 0.0
        self._voice_seen_ms = 0.0

    def process(self, pcm: bytes) -> tuple[bool, bytes | None]:
        if not pcm:
            return False, None
        duration_ms = len(pcm) * 1000.0 / (self.sample_rate * self.channels * 2)
        level = pcm16_rms(pcm)
        active_threshold = max(self.threshold, int(self._noise_floor * 2.8))
        voiced = level >= active_threshold

        started = False
        if not self._speaking:
            if voiced:
                self._speaking = True
                started = True
                for chunk in self._pre_roll:
                    self._utterance.extend(chunk)
                self._pre_roll.clear()
                self._pre_roll_bytes = 0
                self._utterance.extend(pcm)
                self._voice_seen_ms = duration_ms
                self._silence_seen_ms = 0.0
            else:
                self._noise_floor = self._noise_floor * 0.92 + level * 0.08
                self._append_pre_roll(pcm)
            return started, None

        self._utterance.extend(pcm)
        if voiced:
            self._voice_seen_ms += duration_ms
            self._silence_seen_ms = 0.0
        else:
            self._silence_seen_ms += duration_ms

        utterance_ms = len(self._utterance) * 1000.0 / (
            self.sample_rate * self.channels * 2
        )
        if (
            self._silence_seen_ms < self.silence_ms
            and utterance_ms < self.max_utterance_ms
        ):
            return started, None

        completed = bytes(self._utterance) if self._voice_seen_ms >= self.min_voice_ms else None
        self.reset()
        return started, completed

    def _append_pre_roll(self, pcm: bytes) -> None:
        self._pre_roll.append(pcm)
        self._pre_roll_bytes += len(pcm)
        maximum = int(
            self.sample_rate * self.channels * 2 * self.pre_roll_ms / 1000.0
        )
        while self._pre_roll and self._pre_roll_bytes > maximum:
            self._pre_roll_bytes -= len(self._pre_roll.popleft())


class MicrophoneRecorder(QObject):
    recording_changed = Signal(bool)
    listening_changed = Signal(bool)
    speech_started = Signal()
    transcribing_changed = Signal(bool)
    level_changed = Signal(float)
    transcript_ready = Signal(str)
    error = Signal(str)

    def __init__(self, thread_pool: QThreadPool, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread_pool = thread_pool
        self._source: QAudioSource | None = None
        self._device = None
        self._sample_rate = 16_000
        self._channels = 1
        self._paused = False
        self._transcribing = False
        self._segmenter: VoiceActivitySegmenter | None = None

    @property
    def recording(self) -> bool:
        return self._source is not None

    def start(self) -> None:
        if self.recording:
            self.set_paused(False)
            return
        input_device = QMediaDevices.defaultAudioInput()
        if input_device.isNull():
            self.error.emit("No microphone is available.")
            return
        audio_format = self._select_format(input_device)
        if audio_format is None:
            self.error.emit("The microphone does not support PCM voice capture.")
            return
        self._sample_rate = audio_format.sampleRate()
        self._channels = audio_format.channelCount()
        self._segmenter = VoiceActivitySegmenter(
            sample_rate=self._sample_rate,
            channels=self._channels,
            threshold=int(os.getenv("FRIDAY_DESKTOP_MIC_RMS_THRESHOLD", "250")),
            silence_ms=float(os.getenv("FRIDAY_DESKTOP_MIC_SILENCE_MS", "850")),
            max_utterance_ms=float(
                os.getenv("FRIDAY_DESKTOP_MIC_MAX_UTTERANCE_MS", "15000")
            ),
        )
        self._source = QAudioSource(input_device, audio_format, self)
        self._device = self._source.start()
        self._device.readyRead.connect(self._drain)
        self.recording_changed.emit(True)
        self._emit_listening_state()

    def stop(self) -> None:
        if self._source is None:
            return
        self._source.stop()
        self._source.deleteLater()
        self._source = None
        self._device = None
        if self._segmenter is not None:
            self._segmenter.reset()
        self.recording_changed.emit(False)
        self.listening_changed.emit(False)
        self.level_changed.emit(0.0)

    def set_paused(self, paused: bool) -> None:
        if self._paused == paused:
            return
        self._paused = paused
        if self._segmenter is not None:
            self._segmenter.reset()
        if paused:
            self.level_changed.emit(0.0)
        self._emit_listening_state()

    def _submit_utterance(self, pcm: bytes) -> None:
        self._transcribing = True
        self._emit_listening_state()
        self.transcribing_changed.emit(True)
        wav_bytes = pcm_to_wav(
            pcm,
            sample_rate=self._sample_rate,
            channels=self._channels,
        )
        task = FunctionTask(
            lambda: asyncio.run(
                transcribe_core_audio(wav_bytes, content_type="audio/wav", language="en")
            )
        )
        task.signals.completed.connect(self._on_transcription_ready)
        task.signals.failed.connect(self._on_transcription_failed)
        self._thread_pool.start(task)

    def _drain(self) -> None:
        if self._device is None:
            return
        payload = bytes(self._device.readAll())
        if self._paused or self._transcribing or self._segmenter is None:
            self.level_changed.emit(0.0)
            return
        level = pcm16_rms(payload)
        visual_ceiling = max(self._segmenter.threshold * 6, 1)
        self.level_changed.emit(min(1.0, level / visual_ceiling))
        started, utterance = self._segmenter.process(payload)
        if started:
            self.speech_started.emit()
        if utterance:
            self._submit_utterance(utterance)

    def _on_transcription_ready(self, result: object) -> None:
        self._transcribing = False
        self.transcribing_changed.emit(False)
        self.transcript_ready.emit(result.refined_text)
        self._emit_listening_state()

    def _on_transcription_failed(self, message: str) -> None:
        self._transcribing = False
        self.transcribing_changed.emit(False)
        self.error.emit(message)
        self._emit_listening_state()

    def _emit_listening_state(self) -> None:
        self.listening_changed.emit(
            self.recording and not self._paused and not self._transcribing
        )

    @staticmethod
    def _select_format(input_device) -> QAudioFormat | None:
        preferred_rate = input_device.preferredFormat().sampleRate()
        for sample_rate, channels in (
            (16_000, 1),
            (48_000, 1),
            (preferred_rate, 1),
            (preferred_rate, 2),
        ):
            candidate = QAudioFormat()
            candidate.setSampleRate(sample_rate)
            candidate.setChannelCount(channels)
            candidate.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            if input_device.isFormatSupported(candidate):
                return candidate
        return None
