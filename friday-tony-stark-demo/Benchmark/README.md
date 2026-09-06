# FRIDAY Vision Benchmark

This utility inspects the current computer, checks the ONNX Runtime execution
providers installed in the project's virtual environment, runs a lightweight
inference benchmark with FRIDAY's production YOLO model, and selects a
conservative vision profile.

It does not assume a particular GPU model. A detected NVIDIA GPU is only used
when the project environment exposes a compatible CUDA or TensorRT ONNX
provider and that provider successfully initializes the production model.
Otherwise FRIDAY selects CPU compatibility mode and explains why.

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

The report includes model inference latency, full detector-pipeline latency,
and the execution provider that actually ran the model. The benchmark uses a
synthetic 720p frame, so camera lighting and scene complexity do not affect the
backend health check.

On Windows, the project installs `onnxruntime-gpu` together with project-local
CUDA and cuDNN runtime wheels. No global CUDA Toolkit installation is required.
The CPU execution provider remains available as a safe fallback.

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

## Compare detector architectures on one dataset

The hardware benchmark above only verifies that the current runtime works. The
Step 8 detector comparison measures accuracy and end-to-end image latency for
YOLO26n, RF-DETR Nano, and RT-DETRv4-S against the exact same human-reviewed
COCO manifest produced by `friday-vision-annotate`.

Install the optional RF-DETR adapter when that model is being evaluated:

```powershell
uv sync --extra vision-benchmark
```

Set local checkpoint paths in `.env`. FRIDAY never downloads benchmark weights
automatically:

```dotenv
FRIDAY_BENCHMARK_DATASET_ROLE=validation
FRIDAY_BENCHMARK_RFDETR_MODEL=G:\models\rf-detr-nano.pth
FRIDAY_BENCHMARK_RTDETRV4_MODEL=G:\models\rtdetrv4-s.onnx
```

Run the comparison:

```powershell
uv run friday-detector-benchmark `
  --manifest friday\trainModel\vision\annotations\validation\coco.json `
  --dataset-root friday\trainModel\vision `
  --dataset-role validation
```

The command records Precision, Recall, F1, AP50, mAP50:95, average latency,
P95 latency, and FPS. Reports are written below
`friday/trainModel/vision/evaluation/reports/`. A model recommendation is made
only when all three adapters complete on a held-out validation/test set with at
least 50 images. Use `--strict` in automation when missing checkpoints should
produce a non-zero exit code.

## Audit detector licenses before release

FRIDAY defaults to `personal_research`, which keeps the current local YOLO
prototype available but does not approve it for distribution. Run the Step 9
audit explicitly before choosing or packaging a production model:

```powershell
uv run friday-vision-license-audit
uv run friday-vision-license-audit `
  --policy mit_distribution `
  --production-model rfdetr_nano `
  --strict
```

Available policies are `personal_research`, `mit_distribution`, and
`proprietary_distribution`. The audit checks the verified model catalog, the
repository's MIT `LICENSE`, source freshness, the selected production model,
and any configured Ultralytics Enterprise evidence.

For an applicable Ultralytics commercial agreement, keep the evidence outside
the repository and point FRIDAY to it locally:

```dotenv
FRIDAY_ULTRALYTICS_ENTERPRISE_LICENSE_PATH=G:\private\licenses\ultralytics.txt
```

The audit records that evidence exists but cannot determine whether the legal
agreement covers a particular product or deployment. Generated reports are
stored in `Benchmark/reports/`, which is excluded from Git.
