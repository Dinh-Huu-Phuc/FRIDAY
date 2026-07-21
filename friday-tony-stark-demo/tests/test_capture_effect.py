from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from friday.app.computer.capture_effect import controller
from friday.app.computer.capture_effect.geometry import (
    perimeter_length,
    point_on_perimeter,
    trail_points,
)
from friday.app.computer.service import screen_understanding


def test_perimeter_points_stay_on_the_screen_edge() -> None:
    width, height, inset = 1920.0, 1080.0, 5.0
    perimeter = perimeter_length(width, height, inset=inset)

    for step in range(121):
        x, y = point_on_perimeter(
            perimeter * step / 120,
            width,
            height,
            inset=inset,
        )
        assert inset <= x <= width - inset
        assert inset <= y <= height - inset
        on_vertical_edge = x == pytest.approx(inset) or x == pytest.approx(
            width - inset
        )
        on_horizontal_edge = y == pytest.approx(inset) or y == pytest.approx(
            height - inset
        )
        assert on_vertical_edge or on_horizontal_edge


def test_two_trails_have_opposite_heads_and_valid_segments() -> None:
    width, height = 2560.0, 1440.0
    perimeter = perimeter_length(width, height)
    progress = 0.37
    clockwise = trail_points(
        head_distance=progress * perimeter,
        direction=1,
        width=width,
        height=height,
    )
    counter_clockwise = trail_points(
        head_distance=(perimeter / 2.0) - progress * perimeter,
        direction=-1,
        width=width,
        height=height,
    )

    assert len(clockwise) == len(counter_clockwise) == 45
    assert clockwise[-1] != counter_clockwise[-1]
    assert clockwise[0] != clockwise[-1]
    assert counter_clockwise[0] != counter_clockwise[-1]


def test_capture_context_always_finishes_its_process() -> None:
    session = Mock()
    session.start.return_value = True

    with patch.object(controller, "CaptureEffectSession", return_value=session):
        with pytest.raises(RuntimeError, match="capture failed"):
            with controller.screen_capture_animation() as started:
                assert started is True
                raise RuntimeError("capture failed")

    session.finish.assert_called_once_with()


def test_session_accepts_ready_state_from_a_venv_child_pid(tmp_path) -> None:
    launcher = Mock(pid=101)
    launcher.poll.return_value = None
    session = controller.CaptureEffectSession(duration_ms=500)
    session.state_path = tmp_path / "capture-effect.json"

    with patch.object(controller.os, "name", "nt"), patch.object(
        controller.subprocess, "Popen", return_value=launcher
    ), patch.object(
        session,
        "_read_state",
        return_value={"ready": True, "pid": 202},
    ):
        assert session.start() is True

    assert session.process is launcher


def test_screen_observation_runs_inside_the_capture_animation() -> None:
    events: list[str] = []
    expected = SimpleNamespace(screenshot_path="screen.png")

    @contextmanager
    def fake_animation():
        events.append("effect-start")
        yield True
        events.append("effect-finish")

    def fake_observe(request):
        events.append("screenshot")
        assert request.goal == "What am I looking at?"
        assert request.compress_image is True
        assert request.capture_scope == "active"
        return SimpleNamespace(observation=expected)

    with patch.object(screen_understanding, "screen_capture_animation", fake_animation), patch.object(
        screen_understanding, "observe_computer", side_effect=fake_observe
    ):
        result = screen_understanding._observe_current_screen(
            "What am I looking at?"
        )

    assert result is expected
    assert events == ["effect-start", "screenshot", "effect-finish"]


@pytest.mark.parametrize(
    "question",
    [
        "What is displayed across all my screens?",
        "Describe every monitor.",
        "Inspect all of my screens.",
        "Analyze all my monitors.",
    ],
)
def test_all_screen_questions_request_individual_monitor_images(question) -> None:
    assert screen_understanding.is_screen_understanding_request(question)
    assert screen_understanding.wants_all_screens(question)


def test_disabled_effect_does_not_launch_a_process(monkeypatch) -> None:
    monkeypatch.setenv("FRIDAY_CAPTURE_EFFECT_ENABLED", "0")
    session = controller.CaptureEffectSession(duration_ms=500)

    assert session.start() is False
    assert session.process is None
    session.finish()
