# Camera Reasoning Latency

## Scope

Implemented on `camera-reasoning-latency`, based on `origin/master` at
`9c18141`. No new model or replacement perception pipeline. YOLO/ONNX,
ByteTrack, SceneStateStore, SAM2, Grounding DINO, and WorldModel remain intact.
The 896px maximum keyframe edge and JPEG quality 82 remain unchanged.

## Measured Results

Local measurement on 2026-09-07, GTX 1650 Ti (4 GB), existing `gemma3:4b`.
The Ollama resident-model list was empty before the run. The input was a
1280x720 synthetic geometric image, not a webcam frame or personal image.
The repeated request used the same image/question and benefits from prompt
caching. Other desktop workloads were not isolated.

| Measurement | First request, model initially unloaded | Repeated same-image request |
| --- | ---: | ---: |
| FRIDAY vision total | 33,975.38 ms | 6,061.10 ms |
| Frame acquisition (in-memory copy) | 0.66 ms | 0.54 ms |
| JPEG preprocessing/encoding | 81.40 ms | 2.72 ms |
| Scene/world context construction | 0.58 ms | 0.06 ms |
| Ollama client round trip | 33,892.51 ms | 6,057.52 ms |
| Ollama total | 33,707.54 ms | 6,038.36 ms |
| Model load | 14,223.22 ms | 2.60 ms |
| Prompt evaluation | 13,147.84 ms | 335.41 ms |
| Generation/evaluation | 6,290.74 ms | 5,680.43 ms |
| Prompt tokens | 524 | 524 |
| Generated tokens | 94 | 80 |
| Gemma invoked | Yes | Yes |
| Result | Valid answer | Valid answer |

Synthetic fresh structured state, 100 requests: **median 0.023 ms,
p95 0.034 ms**, with no Gemma invocation or image encoding. This measures
reasoning dispatch over already available detections, not detector execution,
STT, TTS, UI scheduling, or end-to-end voice response time.

These are not controlled before/after measurements against the old commit.
The earlier user incident recorded approximately 58 seconds of model startup
and an approximately 120-second failed request. Different inputs, cache state,
and resource availability prevent a direct speedup claim.

The remaining bottlenecks are model loading, image/prompt evaluation, and token
generation. A live changing image cannot be assumed to achieve the repeated
same-image 6-second result. The measurements do not justify lowering resolution.

## Behavioral Changes

- Startup and runtime both use a configurable `30m` keep-alive and matching
  context size. Preload remains a startup-only background operation.
- Runtime output budget defaults to 128 tokens instead of 420. The prompt asks
  for compact JSON. Incomplete JSON produces an explicit fallback, not a broken
  JSON string spoken to the user; valid JSON and plain-text compatibility remain.
- Structured questions run before keyframe acquisition or Gemma. Evidence must
  be visible, at least 0.8 confidence, and no more than 2 seconds old.
- Object lists describe detected classes, not exhaustive scene contents.
  Locations and motion are image-relative. A stationary track does not prove
  stationary limbs. Approaching is a size-trend estimate, not metric depth.
- Holding answers identify a detected hand/object relation without assigning
  personal identity or ownership. Missing relations, stale evidence, multiple
  ambiguous people/objects, and unknown motion fall through to Gemma.
- Semantic questions such as "What is the person doing right now?" still invoke
  Gemma. Motion tracking is not treated as action recognition.
- Current-frame prompts use at most 800 characters of current detector context.
  Named-object historical questions include only the matching entities and their
  events, bounded to 2400 characters. General change/history questions can include
  a bounded broader history. No unrelated history is sent for current questions.
- An already running semantic request does not create an unbounded queue of
  additional VLM work. Additional semantic callers receive a busy fallback;
  structured questions remain available without acquiring the inference lock.
- Offline/timeout/invalid-output fallbacks preserve applicable evidence and
  uncertainty. No raw frame, prompt, or answer is written to latency telemetry.

## Configuration

```dotenv
FRIDAY_VISION_REASONING_KEEP_ALIVE=30m
FRIDAY_VISION_REASONING_NUM_PREDICT=128
```

The local `.env` was updated for these two settings. Existing timeout (120s),
model, context size, and camera resolution were not changed. The example file
keeps values blank. Environment overrides take priority; restart FRIDAY after
changing settings. Keeping the model resident consumes RAM/VRAM longer; lower
the keep-alive on a machine that needs that memory for other applications.

## Inspect Timings

`VisionReasoningResult.timings.to_dict()` exposes:

- `route`, `question_kind`, and `gemma_invoked`;
- `frame_acquisition_ms`, `jpeg_encoding_ms`, `context_build_ms`;
- `dispatch_wait_ms`, `queue_wait_ms`, `ollama_request_ms`, and `total_ms`;
- nested Ollama total/load/prompt-evaluation/generation milliseconds and token
  counts. Missing server metrics are `null`, never invented zeros.

`latency_ms` now means total FRIDAY vision-request time, not just model execution.
Async calls include executor dispatch delay. INFO records from
`friday.app.perception.reasoning.vision_router` contain numerical timing data;
agent neural telemetry also publishes `vision.camera_reasoning.latency`.
Cached answers report no new Gemma invocation and no reused provider timings.

Ollama durations are converted from nanoseconds to milliseconds according to
the [Ollama API documentation](https://github.com/ollama/ollama/blob/main/docs/api.md).

## Verification

The perception, world-model, camera, reasoning, routing, desktop, and web-power
regression suite passed: 215 tests and 29 subtests. Two dependency deprecation
warnings remain in Typer/Click. No live webcam frame-rate measurement was made;
the real model measurements above use a synthetic image.

## Reproduce Locally

Run from `friday-tony-stark-demo`. Structured state only, with no model call:

```powershell
uv run python -m friday.app.perception.reasoning.benchmark
```

Real local Gemma calls using a non-personal synthetic image:

```powershell
uv run python -m friday.app.perception.reasoning.benchmark --synthetic-image --runs 2
```

Use a representative saved camera image for a more realistic measurement:

```powershell
uv run python -m friday.app.perception.reasoning.benchmark --image "C:\images\camera.jpg" --runs 2 --output camera-latency.json
```

The image stays local and is sent only to configured local Ollama. Reports omit
its bytes, path, and answer. `--cold` explicitly unloads the selected model before
the first request; use it only when no other client is using that model. Without
an image option, cold/warm values are explicitly reported as unmeasured.
The benchmark does not launch or stop the existing Ollama server.
