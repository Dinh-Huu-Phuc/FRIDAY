from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from starlette.websockets import WebSocketDisconnect

from friday.app.perception.detection import SceneSnapshot
from friday.app.perception.reasoning import (
    GemmaVisionClient,
    KeyframeReason,
    VisionKeyframe,
    VisionModelError,
    VisionReasoningStatus,
    VisionRouter,
)
from friday.app.perception.reasoning.gemma_vision import VisionModelTimeout
from friday.app.perception.window.intents import camera_analysis_acknowledgement

QUESTION = "What is the person on camera doing?"
ACK = "Let me check the camera, Boss."


def keyframe():
    return VisionKeyframe(
        1,
        10,
        640,
        360,
        KeyframeReason.USER_REQUEST,
        "One person.",
        (),
        jpeg_bytes=b"test-jpeg",
    )


@pytest.mark.parametrize("message", [QUESTION, "FRIDAY, what am I holding?"])
def test_camera_question_has_immediate_feedback(message):
    assert camera_analysis_acknowledgement(message) == ACK


@pytest.mark.parametrize(
    "message", ["open camera", "close camera", "search news", "hello"]
)
def test_other_commands_do_not_receive_analysis_feedback(message):
    assert camera_analysis_acknowledgement(message) == ""


def test_timeout_is_reported_as_incomplete_analysis_not_a_detector_answer():
    def timeout(*args):
        raise httpx.ReadTimeout("slow local model")

    perception = Mock()
    perception.snapshot.return_value = SceneSnapshot(status="ready")
    perception.describe_scene.return_value = "One person is visible."
    perception.describe_world.return_value = "Last observed on the left."
    perception.capture_keyframe.return_value = keyframe()
    client = GemmaVisionClient(requester=timeout, timeout_seconds=120)
    with pytest.raises(VisionModelTimeout, match="120 seconds"):
        client.analyze(QUESTION, keyframe())
    result = VisionRouter(perception, client=client, enabled=True).analyze_sync(
        QUESTION
    )
    assert result.status == VisionReasoningStatus.FALLBACK
    assert "took too long" in result.answer
    assert "not reliably explain" in result.answer
    assert "One person is visible." in result.answer
    assert "Last observed on the left." in result.answer
    assert "120 seconds" in result.error


def test_whitespace_model_answer_does_not_result_in_a_silent_reply():
    client = GemmaVisionClient(
        requester=lambda *args: {"message": {"content": '{"answer":"   "}'}}
    )
    with pytest.raises(VisionModelError, match="blank camera answer"):
        client.analyze(QUESTION, keyframe())


def test_desktop_acknowledges_before_starting_chat_worker():
    from friday.src.UI.static.desktop_ui.window import DesktopWindow

    events = []
    window = SimpleNamespace(
        input=Mock(),
        _busy=False,
        _snapshot={},
        _render_messages=Mock(),
        _set_busy=Mock(),
        _set_status=Mock(),
        _speech=Mock(),
        _thread_pool=Mock(),
        _on_chat_complete=Mock(),
        _on_task_error=Mock(),
    )
    window._speech.enqueue.side_effect = lambda text: events.append(("speak", text))
    window._thread_pool.start.side_effect = lambda task: events.append(("worker", task))
    with (
        patch("friday.src.UI.static.desktop_ui.window.FunctionTask"),
        patch("friday.src.UI.static.desktop_ui.window.record_power_activity"),
    ):
        DesktopWindow.send_message(window, QUESTION, trace_id="camera-test")
    assert events[0] == ("speak", ACK)
    assert events[1][0] == "worker"
    window._set_status.assert_called_once_with(ACK)


def test_web_socket_acknowledges_before_waiting_for_analysis():
    from friday.src.UI.routes import chat_socket

    packets = []
    socket = SimpleNamespace(
        cookies={},
        accept=AsyncMock(),
        receive_json=AsyncMock(
            side_effect=[{"message": QUESTION}, WebSocketDisconnect()]
        ),
        send_json=AsyncMock(side_effect=lambda packet: packets.append(packet)),
    )
    console = Mock()
    console.get_snapshot.return_value = {
        "messages": [{"role": "user"}, {"role": "assistant"}]
    }
    gate = Mock()
    gate.is_unlocked.return_value = True
    power = Mock(sleeping=False)
    power.to_dict.return_value = {"sleeping": False}

    async def chat(request):
        assert request.message == QUESTION
        assert packets[-1] == {"type": "camera_acknowledgement", "message": ACK}
        return {"messages": [{"role": "assistant", "content": "Analysis result"}]}

    with (
        patch("friday.src.UI.routes.get_core_access_gate", return_value=gate),
        patch("friday.src.UI.routes.get_agent_console_service", return_value=console),
        patch("friday.src.UI.routes.get_power_state", return_value=power),
        patch("friday.src.UI.routes.chat", side_effect=chat),
    ):
        asyncio.run(chat_socket(socket))
    assert any(
        packet.get("type") == "snapshot"
        and packet["payload"]["messages"][0].get("content") == "Analysis result"
        for packet in packets
    )
