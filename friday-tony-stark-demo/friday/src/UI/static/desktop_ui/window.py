from __future__ import annotations

import asyncio
import os
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QEvent, QSettings, Qt, QThreadPool, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from friday.app.agent_console.greeting_engine import build_time_greeting
from friday.app.agent_console.schemas import ConsoleChatRequest
from friday.app.agent_console.service import get_agent_console_service
from friday.app.calendar import (
    CalendarReminderEvent,
    get_calendar_reminder_bus,
)
from friday.app.neural_visual import (
    NeuralEventStatus,
    NeuralNodeId,
    NeuralVisualAction,
    emit_neural_activity,
    emit_neural_transfer,
    get_neural_telemetry_bus,
    get_neural_visual_command_bus,
    new_neural_trace_id,
)
from friday.app.power import get_power_state, record_power_activity
from friday.app.research import SEARCH_ACKNOWLEDGEMENT, should_announce_search
from friday.src.services.agent.service import build_startup_briefing, chat
from friday.src.UI.static.browser_ui import SecureBrowserWindowController
from friday.src.UI.static.camera_ui import CameraWindowController
from friday.src.UI.static.code_map_ui import CodeMapWindowController
from friday.src.UI.static.desktop_ui.controllers.tasks import FunctionTask
from friday.src.UI.static.desktop_ui.services.audio import (
    MicrophoneRecorder,
    SpeechPlayer,
)
from friday.src.UI.static.desktop_ui.widgets.audio_waveform import AudioWaveform
from friday.src.UI.static.desktop_ui.widgets.core_visual import CoreVisual
from friday.src.UI.static.desktop_ui.widgets.message_bubble import MessageBubble
from friday.src.UI.static.desktop_ui.widgets.neural_network_visual import (
    NeuralNetworkVisual,
)
from friday.src.UI.static.desktop_ui.widgets.settings_panel import SettingsPanel
from friday.src.UI.static.desktop_ui.widgets.system_status_panel import (
    SystemStatusPanel,
)

FRIDAY_DIR = Path(__file__).resolve().parents[4]
CORE_VIDEO = FRIDAY_DIR / "assets" / "videos" / "FRIDAY.mp4"
SESSION_ID = "python-ui"


class DesktopWindow(QMainWindow):
    closing = Signal()
    calendar_reminder_received = Signal(object)
    neural_visual_action_requested = Signal(str)
    neural_telemetry_received = Signal(object)

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
        self._active_visual = "orb"
        self._visual_before_neural = "orb"
        self._active_trace_id = ""
        self._voice_trace_id = ""

        self._build_ui()
        self._speech = SpeechPlayer(self._thread_pool, self)
        self._speech.set_enabled(self.settings_panel.voice_reply.isChecked())
        self._speech.error.connect(lambda message: self._set_status(f"Voice unavailable: {message}"))
        self._speech.speaking_changed.connect(self._on_speaking_changed)
        self._calendar_reminder_subscriber = (
            lambda event: self.calendar_reminder_received.emit(event)
        )
        self._unsubscribe_calendar_reminders = (
            get_calendar_reminder_bus().subscribe(
                self._calendar_reminder_subscriber
            )
        )
        self.calendar_reminder_received.connect(
            self._on_calendar_reminder,
            Qt.ConnectionType.QueuedConnection,
        )
        self._microphone = MicrophoneRecorder(self._thread_pool, self)
        self._microphone.recording_changed.connect(self._on_recording_changed)
        self._microphone.listening_changed.connect(self._on_listening_changed)
        self._microphone.speech_started.connect(self._on_speech_started)
        self._microphone.transcribing_changed.connect(self._on_transcribing_changed)
        self._microphone.level_changed.connect(self._on_audio_level)
        self._microphone.transcript_ready.connect(self._on_transcript)
        self._microphone.error.connect(lambda message: self._set_status(message))
        self._secure_browser_controller = SecureBrowserWindowController(self)
        self._camera_window_controller = CameraWindowController(self)
        self._code_map_controller = CodeMapWindowController(self)
        self._neural_visual_subscriber = (
            lambda action: self.neural_visual_action_requested.emit(action.value)
        )
        self._unsubscribe_neural_visual = (
            get_neural_visual_command_bus().subscribe(self._neural_visual_subscriber)
        )
        self.neural_visual_action_requested.connect(
            self._apply_neural_visual_action,
            Qt.ConnectionType.QueuedConnection,
        )
        self._neural_telemetry_subscriber = (
            lambda event: self.neural_telemetry_received.emit(event)
        )
        self._unsubscribe_neural_telemetry = (
            get_neural_telemetry_bus().subscribe(self._neural_telemetry_subscriber)
        )
        self.neural_telemetry_received.connect(
            self.neural_visual.ingest_event,
            Qt.ConnectionType.QueuedConnection,
        )

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
        shell.setContentsMargins(16, 0, 16, 14)
        shell.setSpacing(10)

        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top = QHBoxLayout(top_bar)
        top.setContentsMargins(4, 10, 4, 10)
        top.setSpacing(10)

        brand_mark = QLabel("F")
        brand_mark.setObjectName("brandMark")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setFixedSize(34, 34)
        top.addWidget(brand_mark)

        identity = QVBoxLayout()
        identity.setSpacing(1)
        brand = QLabel("FRIDAY Local Core")
        brand.setObjectName("brand")
        identity.addWidget(brand)
        brand_meta = QLabel("NATIVE INTELLIGENCE CONSOLE")
        brand_meta.setObjectName("brandMeta")
        identity.addWidget(brand_meta)
        top.addLayout(identity)
        top.addStretch(1)
        self.connection = QLabel("●  online")
        self.connection.setObjectName("connection")
        self.connection.setText("LOCAL / ONLINE")
        connection_pill = QFrame()
        connection_pill.setObjectName("connectionPill")
        connection_layout = QHBoxLayout(connection_pill)
        connection_layout.setContentsMargins(10, 5, 10, 5)
        connection_layout.setSpacing(7)
        connection_dot = QLabel()
        connection_dot.setObjectName("connectionDot")
        connection_dot.setFixedSize(7, 7)
        connection_layout.addWidget(connection_dot)
        connection_layout.addWidget(self.connection)
        top.addWidget(connection_pill)

        voice_pill = QFrame()
        voice_pill.setObjectName("voicePill")
        voice_layout = QHBoxLayout(voice_pill)
        voice_layout.setContentsMargins(10, 5, 10, 5)
        voice_layout.setSpacing(7)
        voice_dot = QLabel()
        voice_dot.setObjectName("voiceDot")
        voice_dot.setFixedSize(7, 7)
        voice_layout.addWidget(voice_dot)
        self.voice_link = QLabel("VOICE LINK / READY")
        self.voice_link.setObjectName("voiceLink")
        voice_layout.addWidget(self.voice_link)
        top.addWidget(voice_pill)

        self.settings_button = QPushButton("Settings")
        self.settings_button.setObjectName("secondaryButton")
        self.settings_button.setToolTip("Open settings")
        self.settings_button.setFixedHeight(32)
        self.settings_button.clicked.connect(self._toggle_settings)
        top.addWidget(self.settings_button)
        shell.addWidget(top_bar)

        content = QHBoxLayout()
        content.setSpacing(12)
        self.history = self._build_history()
        content.addWidget(self.history)

        stage = QFrame()
        stage.setObjectName("coreStage")
        stage_layout = QVBoxLayout(stage)
        stage_layout.setContentsMargins(0, 0, 0, 0)
        stage_layout.setSpacing(6)
        self.visual_stack = QStackedWidget()
        self.visual_stack.setObjectName("visualStack")
        self.core_visual = CoreVisual()
        self.visual_stack.addWidget(self.core_visual)
        self.neural_visual = NeuralNetworkVisual()
        self.visual_stack.addWidget(self.neural_visual)
        self.video_widget = QVideoWidget()
        self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        self.visual_stack.addWidget(self.video_widget)
        stage_layout.addWidget(self.visual_stack, 1)
        status_strip = QFrame()
        status_strip.setObjectName("statusStrip")
        status_layout = QHBoxLayout(status_strip)
        status_layout.setContentsMargins(12, 7, 12, 7)
        self.kicker = QLabel("FRIDAY / SYSTEM")
        self.kicker.setObjectName("kicker")
        status_layout.addWidget(self.kicker)
        status_layout.addStretch(1)
        self.status = QLabel("Online and ready")
        self.status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.status.setObjectName("status")
        status_layout.addWidget(self.status)
        stage_layout.addWidget(status_strip)
        content.addWidget(stage, 1)

        self.system_panel = SystemStatusPanel()
        content.addWidget(self.system_panel)

        self.settings_panel = SettingsPanel(self._settings)
        self.settings_panel.hide()
        self.settings_panel.visual_changed.connect(self._apply_visual)
        self.settings_panel.voice_changed.connect(self._on_voice_changed)
        self.settings_panel.applied.connect(self._set_status)
        content.addWidget(self.settings_panel)
        shell.addLayout(content, 1)

        command_row = QFrame()
        command_row.setObjectName("commandRow")
        command_row_layout = QHBoxLayout(command_row)
        command_row_layout.setContentsMargins(0, 0, 0, 0)
        command_row_layout.setSpacing(0)
        command_row_layout.addStretch(1)

        command = QFrame()
        command.setObjectName("commandBar")
        command.setMinimumWidth(560)
        command.setMaximumWidth(860)
        command.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        command_layout = QHBoxLayout(command)
        command_layout.setContentsMargins(7, 6, 7, 6)
        command_layout.setSpacing(9)

        mic_core = QLabel("MIC")
        mic_core.setObjectName("micCore")
        mic_core.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mic_core.setFixedSize(44, 44)
        mic_core.setToolTip("Always-on microphone status")
        command_layout.addWidget(mic_core)

        mic_block = QWidget()
        mic_block.setObjectName("micBlock")
        mic_layout = QVBoxLayout(mic_block)
        mic_layout.setContentsMargins(0, 0, 0, 0)
        mic_layout.setSpacing(0)
        self.mic_status = QLabel("MIC  STARTING")
        self.mic_status.setObjectName("micStatus")
        mic_layout.addWidget(self.mic_status)
        self.mic_waveform = AudioWaveform()
        mic_layout.addWidget(self.mic_waveform)
        command_layout.addWidget(mic_block)
        self.input = QTextEdit()
        self.input.setObjectName("commandInput")
        self.input.setPlaceholderText("Talk or type to FRIDAY...")
        self.input.setFixedHeight(44)
        self.input.installEventFilter(self)
        command_layout.addWidget(self.input, 1)
        self.send_button = QPushButton()
        self.send_button.setObjectName("sendButton")
        self.send_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.send_button.setAccessibleName("Send message")
        self.send_button.setToolTip("Send message")
        self.send_button.setFixedSize(46, 46)
        self.send_button.clicked.connect(lambda _checked=False: self.send_message())
        command_layout.addWidget(self.send_button)
        command_row_layout.addWidget(command, 1)
        command_row_layout.addStretch(1)
        shell.addWidget(command_row)

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
        history.setMinimumWidth(306)
        history.setMaximumWidth(326)
        history.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(history)
        layout.setContentsMargins(12, 12, 8, 10)
        layout.setSpacing(8)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        history_title = QLabel("CONVERSATION")
        history_title.setObjectName("sectionTitle")
        titles.addWidget(history_title)
        self.history_count = QLabel("0 MESSAGES / LIVE SESSION")
        self.history_count.setObjectName("sectionMeta")
        titles.addWidget(self.history_count)
        header.addLayout(titles)
        header.addStretch(1)
        clear = QPushButton("Clear")
        clear.setObjectName("ghostButton")
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

    def send_message(
        self,
        text: str | None = None,
        *,
        channel: str = "text",
        trace_id: str = "",
    ) -> None:
        message_source = text if isinstance(text, str) else self.input.toPlainText()
        message = message_source.strip()
        if not message or self._busy:
            return
        resolved_trace_id = trace_id or new_neural_trace_id()
        self._active_trace_id = resolved_trace_id
        if not trace_id:
            emit_neural_activity(
                NeuralNodeId.TEXT_INPUT if channel == "text" else NeuralNodeId.SPEECH_RECOGNITION,
                trace_id=resolved_trace_id,
                event_type="input.received",
                summary=message,
            )
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

        request = ConsoleChatRequest(
            message=message,
            channel=channel,
            session_id=SESSION_ID,
            trace_id=resolved_trace_id,
        )
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
            self._speech.enqueue(
                str(assistant.get("content") or ""),
                trace_id=self._active_trace_id,
            )
        self._active_trace_id = ""
        self._voice_trace_id = ""
        self._set_busy(False)
        self._sync_power_state()

    def _on_task_error(self, message: str) -> None:
        emit_neural_activity(
            NeuralNodeId.RESPONSE,
            trace_id=self._active_trace_id or new_neural_trace_id(),
            event_type="request.failed",
            summary=message,
            status=NeuralEventStatus.ERROR,
        )
        self._active_trace_id = ""
        self._voice_trace_id = ""
        self._set_busy(False)
        self._set_status(f"Request failed: {message}")
        self._load_snapshot()

    def _load_snapshot(self) -> None:
        self._set_snapshot(self._console.get_snapshot(session_id=SESSION_ID))

    def _set_snapshot(self, snapshot: dict) -> None:
        self._snapshot = snapshot
        self._render_messages(snapshot.get("messages") or [])

    def _render_messages(self, messages: list[dict]) -> None:
        self.history_count.setText(f"{len(messages)} MESSAGES / LIVE SESSION")
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
        self.neural_visual.clear_telemetry()
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
        use_neural = visual == "neural"
        active_visual = "video" if use_video else "neural" if use_neural else "orb"
        if active_visual == "neural" and self._active_visual != "neural":
            self._visual_before_neural = self._active_visual
        elif active_visual != "neural":
            self._visual_before_neural = active_visual
        self._active_visual = active_visual
        selected_widget = (
            self.video_widget
            if use_video
            else self.neural_visual
            if use_neural
            else self.core_visual
        )
        self.visual_stack.setCurrentWidget(selected_widget)
        if use_video:
            if not self._video_source_loaded:
                self._video_player.setSource(QUrl.fromLocalFile(str(CORE_VIDEO)))
                self._video_source_loaded = True
            self._video_player.play()
        else:
            self._video_player.pause()
            if visual == "video":
                self._set_status("FRIDAY.mp4 was not found; Core Orb is active")

    def _apply_neural_visual_action(self, value: str) -> None:
        action = NeuralVisualAction(value)
        if action == NeuralVisualAction.OPEN:
            self.settings_panel.select_visual("neural")
            self._set_status("Neural Network active")
        elif action == NeuralVisualAction.CLOSE:
            target = self._visual_before_neural
            if target not in {"orb", "video"}:
                target = "orb"
            self.settings_panel.select_visual(target)
            self._set_status("Neural Network closed")

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
        show_settings = not self.settings_panel.isVisible()
        self.system_panel.setVisible(not show_settings)
        self.settings_panel.setVisible(show_settings)
        self.settings_button.setText("Close" if show_settings else "Settings")

    def _on_voice_changed(self, enabled: bool) -> None:
        self._speech.set_enabled(enabled)
        self._set_status("Voice reply enabled" if enabled else "Voice reply disabled")

    def _on_recording_changed(self, recording: bool) -> None:
        if not recording:
            self.mic_status.setText("MIC  UNAVAILABLE")
            self.voice_link.setText("VOICE LINK / OFFLINE")

    def _on_listening_changed(self, listening: bool) -> None:
        self.mic_status.setText("MIC  LISTENING" if listening else "MIC  PAUSED")
        self.voice_link.setText(
            "VOICE LINK / READY" if listening else "VOICE LINK / STANDBY"
        )

    def _on_speech_started(self) -> None:
        self._voice_trace_id = new_neural_trace_id()
        emit_neural_activity(
            NeuralNodeId.MICROPHONE,
            trace_id=self._voice_trace_id,
            event_type="microphone.speech.started",
            summary="Live speech detected",
        )
        self.mic_status.setText("MIC  HEARING")
        self.voice_link.setText("VOICE LINK / HEARING")
        self._set_status("Listening")
        self._set_visual_state("listening")

    def _on_transcribing_changed(self, transcribing: bool) -> None:
        if transcribing:
            trace_id = self._voice_trace_id or new_neural_trace_id()
            self._voice_trace_id = trace_id
            emit_neural_transfer(
                NeuralNodeId.MICROPHONE,
                NeuralNodeId.SPEECH_RECOGNITION,
                trace_id=trace_id,
                event_type="stt.transcription.started",
                summary="Captured audio sent for speech recognition",
            )
            self.mic_status.setText("MIC  PROCESSING")
            self.voice_link.setText("VOICE LINK / PROCESSING")
            self._set_status("Transcribing")
            self._set_visual_state("thinking")

    def _on_audio_level(self, level: float) -> None:
        self.mic_waveform.set_level(level)
        self.core_visual.set_audio_level(level)

    def _on_speaking_changed(self, active: bool) -> None:
        self._voice_active = active
        self.voice_link.setText(
            "VOICE LINK / SPEAKING" if active else "VOICE LINK / READY"
        )
        self._set_visual_state(
            "speaking"
            if active
            else (
                "sleeping"
                if self._sleeping
                else ("thinking" if self._busy else "online")
            )
        )
        self._update_microphone_gate()

    def _on_calendar_reminder(self, event: object) -> None:
        if not isinstance(event, CalendarReminderEvent):
            return
        if event.message is not None and not event.sleeping:
            self._load_snapshot()
            self._set_status(f"Reminder: {event.title}")
        if event.audio_target in {"desktop", "all"}:
            self._speech.enqueue(
                event.spoken_text,
                trace_id=event.trace_id,
            )

    def _on_transcript(self, text: str) -> None:
        self.input.setPlainText(text)
        self.send_message(
            text,
            channel="voice",
            trace_id=self._voice_trace_id or new_neural_trace_id(),
        )

    def _sync_power_state(self) -> None:
        sleeping = get_power_state().sleeping
        if sleeping == self._sleeping:
            return
        self._sleeping = sleeping
        self._microphone.set_sleeping(sleeping)
        if sleeping:
            self._set_visual_state("sleeping")
            self._secure_browser_controller.close_all_windows()
            self._camera_window_controller.close_window()
            self._code_map_controller.close_window()
            self.hide()
        else:
            self._set_visual_state("thinking" if self._busy else "online")
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.send_button.setEnabled(not busy)
        self._set_visual_state("thinking" if busy else "online")
        self._update_microphone_gate()

    def _set_visual_state(self, state: str) -> None:
        self.core_visual.set_state(state)
        self.neural_visual.set_state(state)
        self.system_panel.set_core_state(state)

    def _update_microphone_gate(self) -> None:
        if hasattr(self, "_microphone"):
            self._microphone.set_paused(self._busy or self._voice_active)

    def _set_status(self, message: str) -> None:
        self.status.setText(message)

    def closeEvent(self, event) -> None:
        self._unsubscribe_calendar_reminders()
        self._unsubscribe_neural_visual()
        self._unsubscribe_neural_telemetry()
        self._secure_browser_controller.shutdown()
        self._camera_window_controller.shutdown()
        self._code_map_controller.shutdown()
        if self._microphone.recording:
            self._microphone.stop()
        self._speech.set_enabled(False)
        self._video_player.stop()
        self.closing.emit()
        super().closeEvent(event)
