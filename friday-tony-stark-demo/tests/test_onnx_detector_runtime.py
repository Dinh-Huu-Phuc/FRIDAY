from __future__ import annotations

import sys
from types import SimpleNamespace

from friday.app.perception.detection.onnx_detector import OnnxObjectDetector


def test_cuda_runtime_is_preloaded_and_failed_session_retries_on_cpu(
    monkeypatch,
    tmp_path,
) -> None:
    calls: list[tuple[str, ...]] = []
    preloads: list[str] = []

    class FakeSession:
        def __init__(self, providers):
            self._providers = tuple(providers)

        def get_inputs(self):
            return [SimpleNamespace(name="images", shape=(1, 3, 640, 640))]

        def get_outputs(self):
            return [SimpleNamespace(name="output")]

        def get_providers(self):
            return list(self._providers)

        def get_modelmeta(self):
            return SimpleNamespace(custom_metadata_map={"names": "{0: 'person'}"})

    def inference_session(path, *, sess_options, providers):
        del path, sess_options
        calls.append(tuple(providers))
        if providers[0] == "CUDAExecutionProvider":
            raise RuntimeError("CUDA DLL load failed")
        return FakeSession(providers)

    fake_ort = SimpleNamespace(
        SessionOptions=lambda: SimpleNamespace(graph_optimization_level=None),
        GraphOptimizationLevel=SimpleNamespace(ORT_ENABLE_ALL="all"),
        get_available_providers=lambda: [
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ],
        preload_dlls=lambda *, directory: preloads.append(directory),
        InferenceSession=inference_session,
    )
    monkeypatch.setitem(sys.modules, "onnxruntime", fake_ort)
    model_path = tmp_path / "detector.onnx"
    model_path.write_bytes(b"test")

    detector = OnnxObjectDetector(
        model_path,
        providers=("CUDAExecutionProvider", "CPUExecutionProvider"),
    )

    assert preloads == [""]
    assert calls == [
        ("CUDAExecutionProvider", "CPUExecutionProvider"),
        ("CPUExecutionProvider",),
    ]
    assert detector.providers == ("CPUExecutionProvider",)
