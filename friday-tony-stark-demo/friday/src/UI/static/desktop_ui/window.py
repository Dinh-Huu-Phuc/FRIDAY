from __future__ import annotations

import asyncio
import os
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QEvent, QSettings, QThreadPool, QTimer, Qt, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from friday.app.agent_console.greeting_engine import build_time_greeting
from friday.app.agent_console.schemas import ConsoleChatRequest
from friday.app.agent_console.service import get_agent_console_service
from friday.app.power import get_power_state, record_power_activity
from friday.app.research import SEARCH_ACKNOWLEDGEMENT, should_announce_search
from friday.src.UI.static.desktop_ui.controllers.tasks import FunctionTask
from friday.src.UI.static.desktop_ui.services.audio import MicrophoneRecorder, SpeechPlayer
from friday.src.UI.static.desktop_ui.widgets.audio_waveform import AudioWaveform
from friday.src.UI.static.desktop_ui.widgets.core_visual import CoreVisual
from friday.src.UI.static.desktop_ui.widgets.message_bubble import MessageBubble
from friday.src.UI.static.desktop_ui.widgets.settings_panel import SettingsPanel
from friday.src.services.agent.service import build_startup_briefing, chat


FRIDAY_DIR = Path(__file__).resolve().parents[4]
CORE_VIDEO = FRIDAY_DIR / "assets" / "videos" / "FRIDAY.mp4"
SESSION_ID = "python-ui"


class DesktopWindow(QMainWindow):
    closing = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("FRIDAY Local Core")
        self.setMinimumSize(1080, 680)
        self.resize(1440, 860)
        self._settings = QSettings("FRIDAY", "LocalCore")
        self._thread_pool = QThreadPool.globalInstance()
        self._console = get_agent_console_service()
        self._snapshot: dict = {}
        self._last_spoken_message_id = ""
        self._sleeping = False
        self._busy = False
        self._voice_active = False

        self._build_ui()
        self._speech = SpeechPlayer(self._thread_pool, self)
        self._speech.set_enabled(self.settings_panel.voice_reply.isChecked())
        self._speech.error.connect(lambda message: self._set_status(f"Voice unavailable: {message}"))
        self._speech.speaking_changed.connect(self._on_speaking_changed)
        self._microphone = MicrophoneRecorder(self._thread_pool, self)
        self._microphone.recording_changed.connect(self._on_recording_changed)
        self._microphone.listening_changed.connect(self._on_listening_changed)
        self._microphone.speech_started.connect(self._on_speech_started)
        self._microphone.transcribing_changed.connect(self._on_transcribing_changed)
        self._microphone.level_changed.connect(self._on_audio_level)
        self._microphone.transcript_ready.connect(self._on_transcript)
        self._microphone.error.connect(lambda message: self._set_status(message))

        self._load_snapshot()
        self._apply_visual(str(self._settings.value("appearance/visual", "orb")))
        self._power_timer = QTimer(self)
        self._power_timer.timeout.connect(self._sync_power_state)
        self._power_timer.start(500)
        QTimer.singleShot(0, self._microphone.start)
        QTimer.singleShot(250, self._maybe_start_briefing)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        shell = QVBoxLayout(root)
        shell.setContentsMargins(18, 14, 18, 16)
        shell.setSpacing(12)

        top = QHBoxLayout()
        brand = QLabel("FRIDAY  /  LOCAL CORE")
        brand.setObjectName("brand")
        top.addWidget(brand)
        top.addStretch(1)
        self.connection = QLabel("●  online")
        self.connection.setObjectName("connection")
        top.addWidget(self.connection)
        self.settings_button = QPushButton("Settings")
        self.settings_button.setToolTip("Open settings")
        self.settings_button.clicked.connect(self._toggle_settings)
        top.addWidget(self.settings_button)
        shell.addLayout(top)

        content = QHBoxLayout()
        content.setSpacing(14)
        self.history = self._build_history()
        content.addWidget(self.history)

        stage = QFrame()
        stage.setObjectName("coreStage")
        stage_layout = QVBoxLayout(stage)
        stage_layout.setContentsMargins(20, 18, 20, 18)
        stage_layout.setSpacing(6)
        self.visual_stack = QStackedWidget()
        self.core_visual = CoreVisual()
        self.visual_stack.addWidget(self.core_visual)
        self.video_widget = QVideoWidget()
        self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        self.visual_stack.addWidget(self.video_widget)
        stage_layout.addWidget(self.visual_stack, 1)
        self.kicker = QLabel("FRIDAY LOCAL CORE")
        self.kicker.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.kicker.setObjectName("kicker")
        stage_layout.addWidget(self.kicker)
        self.status = QLabel("Online and ready")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setObjectName("status")
        stage_layout.addWidget(self.status)
        content.addWidget(stage, 1)

        self.settings_panel = SettingsPanel(self._settings)
        self.settings_panel.hide()
        self.settings_panel.visual_changed.connect(self._apply_visual)
        self.settings_panel.voice_changed.connect(self._on_voice_changed)
        self.settings_panel.applied.connect(self._set_status)
        content.addWidget(self.settings_panel)
        shell.addLayout(content, 1)

        command = QFrame()
        command.setObjectName("commandBar")
        command_layout = QHBoxLayout(command)
        command_layout.setContentsMargins(8, 7, 8, 7)
        self.mic_status = QLabel("MIC  STARTING")
        self.mic_status.setObjectName("micStatus")
        self.mic_status.setMinimumWidth(112)
        command_layout.addWidget(self.mic_status)
        self.mic_waveform = AudioWaveform()
        command_layout.addWidget(self.mic_waveform)
        self.input = QTextEdit()
        self.input.setObjectName("commandInput")
        self.input.setPlaceholderText("Talk or type to FRIDAY...")
        self.input.setFixedHeight(48)
        self.input.installEventFilter(self)
        command_layout.addWidget(self.input, 1)
        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("primaryButton")
        self.send_button.setFixedWidth(82)
        self.send_button.clicked.connect(self.send_message)
        command_layout.addWidget(self.send_button)
        shell.addWidget(command)

        self._video_audio = QAudioOutput(self)
        self._video_audio.setMuted(True)
        self._video_player = QMediaPlayer(self)
        self._video_player.setAudioOutput(self._video_audio)
        self._video_player.setVideoOutput(self.video_widget)
        self._video_player.setLoops(QMediaPlayer.Loops.Infinite)
        self._video_source_loaded = False
        self._video_player.errorOccurred.connect(
            lambda _error, message: self._handle_video_error(message)
        )
        self._video_player.mediaStatusChanged.connect(self._on_video_status)

    def _build_history(self) -> QFrame:
        history = QFrame()
        history.setObjectName("historyPanel")
        history.setFixedWidth(390)
        layout = QVBoxLayout(history)
        layout.setContentsMargins(12, 12, 12, 12)
        header = QHBoxLayout()
        header.addWidget(QLabel("CONVERSATION"))
        header.addStretch(1)
        clear = QPushButton("Clear")
        clear.setToolTip("Archive and clear conversation")
        clear.clicked.connect(self._clear_chat)
        header.addWidget(clear)
        layout.addLayout(header)
        self.message_scroll = QScrollArea()
        self.message_scroll.setWidgetResizable(True)
        self.message_scroll.setFrameShape(QFrame.Shape.NoFrame)
        message_host = QWidget()
        self.message_layout = QVBoxLayout(message_host)
        self.message_layout.setContentsMargins(0, 6, 4, 6)
        self.message_layout.setSpacing(10)
        self.message_layout.addStretch(1)
        self.message_scroll.setWidget(message_host)
        layout.addWidget(self.message_scroll, 1)
        return history

    def eventFilter(self, watched, event) -> bool:
        if watched is self.input and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
                event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            ):
                self.send_message()
                return True
        return super().eventFilter(watched, event)

    def send_message(self, text: str | None = None, *, channel: str = "text") -> None:
        message = (text if text is not None else self.input.toPlainText()).strip()
        if not message or self._busy:
            return
        self.input.clear()
        record_power_activity(source="desktop_ui")
        pending = list(self._snapshot.get("messages") or [])
        pending.append({
            "id": f"pending-{uuid4().hex[:8]}",
            "role": "user",
            "content": message,
            "status": "pending",
            "channel": channel,
        })
        self._render_messages(pending)
        self._set_busy(True)
        if should_announce_search(message):
            self._set_status(SEARCH_ACKNOWLEDGEMENT)
            self._speech.enqueue(SEARCH_ACKNOWLEDGEMENT)
        else:
            self._set_status("Thinking")

        request = ConsoleChatRequest(message=message, channel=channel, session_id=SESSION_ID)
        task = FunctionTask(lambda: asyncio.run(chat(request)))
        task.signals.completed.connect(self._on_chat_complete)
        task.signals.failed.connect(self._on_task_error)
        self._thread_pool.start(task)

    def _on_chat_complete(self, payload: object) -> None:
        self._set_snapshot(dict(payload))
        self._set_status("Online and ready")
        messages = self._snapshot.get("messages") or []
        assistant = next((item for item in reversed(messages) if item.get("role") == "assistant"), None)
        if assistant and assistant.get("id") != self._last_spoken_message_id:
            self._last_spoken_message_id = str(assistant.get("id"))
            self._speech.enqueue(str(assistant.get("content") or ""))
        self._set_busy(False)
        self._sync_power_state()

    def _on_task_error(self, message: str) -> None:
        self._set_busy(False)
        self._set_status(f"Request failed: {message}")
        self._load_snapshot()

    def _load_snapshot(self) -> None:
        self._set_snapshot(self._console.get_snapshot(session_id=SESSION_ID))

    def _set_snapshot(self, snapshot: dict) -> None:
        self._snapshot = snapshot
        self._render_messages(snapshot.get("messages") or [])

    def _render_messages(self, messages: list[dict]) -> None:
        while self.message_layout.count() > 1:
            item = self.message_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for message in messages:
            wrapper = QWidget()
            row = QHBoxLayout(wrapper)
            row.setContentsMargins(0, 0, 0, 0)
            bubble = MessageBubble(message)
            if message.get("role") == "user":
                row.addStretch(1)
                row.addWidget(bubble)
            else:
                row.addWidget(bubble)
                row.addStretch(1)
            self.message_layout.insertWidget(self.message_layout.count() - 1, wrapper)
        QTimer.singleShot(0, lambda: self.message_scroll.verticalScrollBar().setValue(
            self.message_scroll.verticalScrollBar().maximum()
        ))

    def _clear_chat(self) -> None:
        snapshot = self._console.archive_and_reset_chat(session_id=SESSION_ID, reason="desktop_clear")
        self._set_snapshot(snapshot)
        self._set_status("Conversation archived and cleared")

    def _maybe_start_briefing(self) -> None:
        if get_power_state().sleeping:
            return
        briefing_enabled = os.getenv(
            "FRIDAY_DESKTOP_STARTUP_BRIEFING", "false"
        ).lower() in {"1", "true", "yes", "on"}
        quick = build_time_greeting(event="startup")
        if briefing_enabled:
            quick = f"{quick} Live information is warming up in the background."
        if len(self._snapshot.get("messages") or []) <= 1:
            self._set_snapshot(
                self._console.add_assistant_message(
                    session_id=SESSION_ID,
                    content=quick,
                )
            )
        self._speech.enqueue(quick)
        if not briefing_enabled:
            return
        task = FunctionTask(lambda: asyncio.run(build_startup_briefing()))
        task.signals.completed.connect(self._on_briefing_ready)
        task.signals.failed.connect(lambda _message: None)
        self._thread_pool.start(task)

    def _on_briefing_ready(self, content: object) -> None:
        if get_power_state().sleeping:
            return
        snapshot = self._console.add_assistant_message(session_id=SESSION_ID, content=str(content))
        self._set_snapshot(snapshot)

    def _apply_visual(self, visual: str) -> None:
        use_video = visual == "video" and CORE_VIDEO.is_file()
        self.visual_stack.setCurrentWidget(self.video_widget if use_video else self.core_visual)
        if use_video:
            if not self._video_source_loaded:
                self._video_player.setSource(QUrl.fromLocalFile(str(CORE_VIDEO)))
                self._video_source_loaded = True
            self._video_player.play()
        else:
            self._video_player.pause()
            if visual == "video":
                self._set_status("FRIDAY.mp4 was not found; Core Orb is active")

    def _on_video_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.InvalidMedia:
            self._handle_video_error("The selected video cannot be decoded.")

    def _handle_video_error(self, message: str) -> None:
        if self.visual_stack.currentWidget() is not self.video_widget:
            return
        self._video_player.stop()
        self.visual_stack.setCurrentWidget(self.core_visual)
        self._set_status(f"Video unavailable: {message or 'unsupported media'}")

    def _toggle_settings(self) -> None:
        self.settings_panel.setVisible(not self.settings_panel.isVisible())

    def _on_voice_changed(self, enabled: bool) -> None:
        self._speech.set_enabled(enabled)
        self._set_status("Voice reply enabled" if enabled else "Voice reply disabled")

    def _on_recording_changed(self, recording: bool) -> None:
        if not recording:
            self.mic_status.setText("MIC  UNAVAILABLE")

    def _on_listening_changed(self, listening: bool) -> None:
        self.mic_status.setText("MIC  LISTENING" if listening else "MIC  PAUSED")

    def _on_speech_started(self) -> None:
        self.mic_status.setText("MIC  HEARING")
        self._set_status("Listening")

    def _on_transcribing_changed(self, transcribing: bool) -> None:
        if transcribing:
            self.mic_status.setText("MIC  PROCESSING")
            self._set_status("Transcribing")

    def _on_audio_level(self, level: float) -> None:
        self.mic_waveform.set_level(level)

    def _on_speaking_changed(self, active: bool) -> None:
        self._voice_active = active
        self.core_visual.set_state(
            "speaking" if active else ("thinking" if self._busy else "online")
        )
        self._update_microphone_gate()

    def _on_transcript(self, text: str) -> None:
        self.input.setPlainText(text)
        self.send_message(text, channel="voice")

    def _sync_power_state(self) -> None:
        sleeping = get_power_state().sleeping
        if sleeping == self._sleeping:
            return
        self._sleeping = sleeping
        if sleeping:
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.send_button.setEnabled(not busy)
        self.core_visual.set_state("thinking" if busy else "online")
        self._update_microphone_gate()

    def _update_microphone_gate(self) -> None:
        if hasattr(self, "_microphone"):
            self._microphone.set_paused(self._busy or self._voice_active)

    def _set_status(self, message: str) -> None:
        self.status.setText(message)

    def closeEvent(self, event) -> None:
        if self._microphone.recording:
            self._microphone.stop()
        self._speech.set_enabled(False)
        self._video_player.stop()
        self.closing.emit()
        super().closeEvent(event)
