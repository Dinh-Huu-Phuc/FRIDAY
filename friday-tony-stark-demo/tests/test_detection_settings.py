from friday.app.perception.detection import get_detection_target_fps


def test_detector_target_fps_can_be_tuned_without_replacing_profile(monkeypatch) -> None:
    monkeypatch.setenv("FRIDAY_VISION_DETECTOR_TARGET_FPS", "12")
    assert get_detection_target_fps(3) == 12

    monkeypatch.setenv("FRIDAY_VISION_DETECTOR_TARGET_FPS", "99")
    assert get_detection_target_fps(3) == 30
