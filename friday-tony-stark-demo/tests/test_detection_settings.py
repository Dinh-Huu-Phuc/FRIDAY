from friday.app.perception.detection import get_detection_target_fps


def test_detector_target_fps_can_be_tuned_without_replacing_profile(monkeypatch) -> None:
    monkeypatch.setenv("FRIDAY_VISION_DETECTOR_TARGET_FPS", "12")
    assert get_detection_target_fps(3) == 12

    monkeypatch.setenv("FRIDAY_VISION_DETECTOR_TARGET_FPS", "99")
    assert get_detection_target_fps(3) == 30


def test_blank_or_auto_detector_target_uses_selected_profile(monkeypatch) -> None:
    monkeypatch.setenv("FRIDAY_VISION_DETECTOR_TARGET_FPS", "")
    assert get_detection_target_fps(7) == 7

    monkeypatch.setenv("FRIDAY_VISION_DETECTOR_TARGET_FPS", "auto")
    assert get_detection_target_fps(3) == 3
