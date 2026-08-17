from friday.app.perception.camera.settings import (
    get_camera_render_fps,
    get_default_camera_index,
    get_hud_smoothing_ms,
)
from friday.app.spatial.config import get_spatial_config


def test_camera_index_comes_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("FRIDAY_CAMERA_INDEX", "1")

    assert get_default_camera_index() == 1
    assert get_spatial_config().camera_index == 1


def test_invalid_camera_index_falls_back_to_zero(monkeypatch) -> None:
    monkeypatch.setenv("FRIDAY_CAMERA_INDEX", "not-a-number")
    assert get_default_camera_index() == 0

    monkeypatch.setenv("FRIDAY_CAMERA_INDEX", "-2")
    assert get_default_camera_index() == 0


def test_camera_hud_performance_settings_are_bounded(monkeypatch) -> None:
    monkeypatch.setenv("FRIDAY_CAMERA_RENDER_FPS", "60")
    monkeypatch.setenv("FRIDAY_CAMERA_HUD_SMOOTHING_MS", "110")
    assert get_camera_render_fps() == 60
    assert get_hud_smoothing_ms() == 110

    monkeypatch.setenv("FRIDAY_CAMERA_RENDER_FPS", "500")
    monkeypatch.setenv("FRIDAY_CAMERA_HUD_SMOOTHING_MS", "1")
    assert get_camera_render_fps() == 120
    assert get_hud_smoothing_ms() == 40
