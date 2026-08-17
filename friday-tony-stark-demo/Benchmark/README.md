# FRIDAY Vision Benchmark

This utility inspects the current computer, checks the ONNX Runtime execution
providers installed in the project's virtual environment, runs a lightweight
OpenCV preprocessing benchmark, and selects a conservative vision profile.

It does not assume a particular GPU model. A detected NVIDIA GPU is only used
when the project environment also exposes a compatible CUDA or TensorRT ONNX
provider. Otherwise FRIDAY selects CPU compatibility mode and explains why.

## Run from source

```powershell
uv run python Benchmark/main.py
```

Preview the decision without updating `.env`:

```powershell
uv run python Benchmark/main.py --no-apply-env
```

## Run the executable

```powershell
Benchmark\dist\FRIDAYVisionBenchmark.exe
```

The executable should remain inside this project tree so it can inspect the
current `.venv`. It writes the latest report to
`Benchmark/reports/friday_vision_benchmark_latest.json` and updates only the
resolved vision keys in `.env`.

## Rebuild the executable

```powershell
powershell -ExecutionPolicy Bypass -File Benchmark/build_exe.ps1
```

The reported OpenCV number measures input preprocessing, not neural-network
inference. It is used as a basic health signal; the backend decision is driven
primarily by real runtime-provider availability and GPU memory.

## Select a camera

Probe the camera indexes available through OpenCV:

```powershell
uv run python Benchmark/camera_probe.py
```

Set the desired index in `.env`, then restart FRIDAY:

```dotenv
FRIDAY_CAMERA_INDEX=1
```

Camera Window and Spatial both use this value and share the same capture.
