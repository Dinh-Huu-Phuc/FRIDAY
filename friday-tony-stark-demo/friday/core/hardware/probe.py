from __future__ import annotations

import ctypes
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from friday.core.hardware.schemas import GpuDevice, HardwareSnapshot

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def find_project_root(start: str | Path | None = None) -> Path:
    candidates = [
        Path(start).resolve() if start else Path.cwd().resolve(),
        Path(sys.executable).resolve().parent,
        Path(__file__).resolve().parent,
    ]
    for candidate in candidates:
        for parent in (candidate, *candidate.parents):
            if (parent / "pyproject.toml").is_file() and (parent / "friday").is_dir():
                return parent
    return Path(start).resolve() if start else Path.cwd().resolve()


def project_python(project_root: Path) -> Path | None:
    candidates = (
        project_root / ".venv" / "Scripts" / "python.exe",
        project_root / ".venv" / "bin" / "python",
    )
    return next((path for path in candidates if path.is_file()), None)


def _run(command: list[str], *, timeout: float = 8.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        creationflags=_NO_WINDOW,
    )


def _probe_onnx_runtime(project_root: Path) -> tuple[str, tuple[str, ...], str]:
    python = project_python(project_root)
    if python is None:
        return "", (), "Project virtual environment was not found; ONNX providers were not probed."

    script = (
        "import json\n"
        "try:\n"
        " import onnxruntime as ort\n"
        " print(json.dumps({'ok': True, 'version': ort.__version__, "
        "'providers': ort.get_available_providers()}))\n"
        "except Exception as exc:\n"
        " print(json.dumps({'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}))\n"
    )
    try:
        completed = _run([str(python), "-c", script])
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, IndexError) as exc:
        return "", (), f"ONNX Runtime probe failed: {type(exc).__name__}."

    if not payload.get("ok"):
        return "", (), f"ONNX Runtime is unavailable: {payload.get('error', 'unknown error')}"
    providers = tuple(str(item) for item in payload.get("providers") or ())
    return str(payload.get("version") or ""), providers, ""


def _probe_nvidia_gpus() -> tuple[tuple[GpuDevice, ...], str]:
    executable = shutil.which("nvidia-smi")
    if not executable and os.name == "nt":
        candidate = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "nvidia-smi.exe"
        if candidate.is_file():
            executable = str(candidate)
    if not executable:
        return (), "nvidia-smi was not found."

    fields = "name,memory.total,memory.free,driver_version,compute_cap"
    try:
        completed = _run(
            [executable, f"--query-gpu={fields}", "--format=csv,noheader,nounits"]
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return (), f"NVIDIA GPU probe failed: {type(exc).__name__}."
    if completed.returncode != 0:
        return (), "nvidia-smi could not return GPU details."

    devices: list[GpuDevice] = []
    for line in completed.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 5:
            continue
        try:
            total_memory = int(float(parts[1]))
            free_memory = int(float(parts[2]))
        except ValueError:
            total_memory = None
            free_memory = None
        devices.append(
            GpuDevice(
                name=parts[0],
                total_memory_mb=total_memory,
                free_memory_mb=free_memory,
                driver_version=parts[3],
                compute_capability=parts[4],
            )
        )
    return tuple(devices), "" if devices else "No NVIDIA GPU was reported by nvidia-smi."


def _system_memory_mb() -> int | None:
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.total_physical / (1024 * 1024))
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        page_count = os.sysconf("SC_PHYS_PAGES")
        return int(page_size * page_count / (1024 * 1024))
    except (AttributeError, OSError, ValueError):
        return None


def _operating_system_name() -> str:
    if os.name == "nt":
        version = sys.getwindowsversion()
        release = "11" if version.build >= 22000 else "10"
        return f"Windows {release} build {version.build} ({platform.machine()})"
    return f"{platform.system()} {platform.release()} ({platform.machine()})"


def probe_hardware(project_root: str | Path | None = None) -> HardwareSnapshot:
    root = find_project_root(project_root)
    warnings: list[str] = []
    ort_version, providers, ort_warning = _probe_onnx_runtime(root)
    if ort_warning:
        warnings.append(ort_warning)
    gpus, gpu_warning = _probe_nvidia_gpus()
    if gpu_warning and not gpus:
        warnings.append(gpu_warning)

    cpu_name = platform.processor().strip() or os.getenv("PROCESSOR_IDENTIFIER", "Unknown CPU")
    return HardwareSnapshot(
        operating_system=_operating_system_name(),
        cpu_name=cpu_name,
        logical_cpu_count=os.cpu_count() or 1,
        system_memory_mb=_system_memory_mb(),
        gpus=gpus,
        onnx_runtime_version=ort_version,
        onnx_providers=providers,
        probe_warnings=tuple(warnings),
    )
