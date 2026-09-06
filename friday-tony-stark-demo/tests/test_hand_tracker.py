import sys
from types import SimpleNamespace

from friday.app.spatial.service.hand_tracker import HandTracker


class _FakeLandmarker:
    created_options = None

    @classmethod
    def create_from_options(cls, options):
        cls.created_options = options
        return cls()

    def detect_for_video(self, image, timestamp_ms):
        assert image.data == "rgb-frame"
        assert timestamp_ms > 0
        point = SimpleNamespace(x=0.25, y=0.75, z=-0.1)
        category = SimpleNamespace(
            category_name="Right",
            display_name=None,
            score=0.93,
        )
        return SimpleNamespace(
            hand_landmarks=[[point]],
            handedness=[[category]],
        )

    def close(self) -> None:
        return


class _FakeOptions:
    def __init__(self, **values):
        self.__dict__.update(values)


class _FakeImage:
    def __init__(self, *, image_format, data):
        self.image_format = image_format
        self.data = data


def test_hand_tracker_uses_mediapipe_tasks_api(monkeypatch, tmp_path) -> None:
    model_path = tmp_path / "hand_landmarker.task"
    model_path.write_bytes(b"model")
    monkeypatch.setenv("FRIDAY_MEDIAPIPE_HAND_MODEL", str(model_path))

    fake_cv2 = SimpleNamespace(
        COLOR_BGR2RGB=4,
        cvtColor=lambda frame, code: "rgb-frame",
    )
    fake_vision = SimpleNamespace(
        HandLandmarker=_FakeLandmarker,
        HandLandmarkerOptions=_FakeOptions,
        RunningMode=SimpleNamespace(VIDEO="video"),
    )
    fake_tasks = SimpleNamespace(BaseOptions=_FakeOptions, vision=fake_vision)
    fake_mp = SimpleNamespace(
        tasks=fake_tasks,
        Image=_FakeImage,
        ImageFormat=SimpleNamespace(SRGB="srgb"),
    )
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.setitem(sys.modules, "mediapipe", fake_mp)

    tracker = HandTracker()
    hands = tracker.detect(object())

    assert tracker.backend == "tasks"
    assert hands == [
        {
            "hand": "right",
            "hand_confidence": 0.93,
            "points": {0: (0.25, 0.75, -0.1)},
        }
    ]
    assert _FakeLandmarker.created_options.num_hands == 2
    assert _FakeLandmarker.created_options.running_mode == "video"
    tracker.close()
    assert tracker.backend is None
