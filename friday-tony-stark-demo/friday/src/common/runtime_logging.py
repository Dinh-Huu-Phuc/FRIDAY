from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WARNING_LOG = PROJECT_ROOT / "friday" / "log" / "runtime" / "friday-warnings.log"
QUIET_LOGGERS = ("livekit.agents", "friday-refiner")
CONSOLE_NOISE_MARKERS = (
    "failed to synthesize speech:",
    "AudioByteStream: incomplete frame during flush, dropping",
    "STT refiner provider_failed=",
    "STT refiner provider_unexpected=",
)


class RuntimeConsoleNoiseFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not any(marker in message for marker in CONSOLE_NOISE_MARKERS)


def _runtime_log_path() -> Path:
    configured = os.getenv("FRIDAY_RUNTIME_WARNING_LOG", "").strip()
    path = Path(configured).expanduser() if configured else DEFAULT_WARNING_LOG
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def _is_verbose() -> bool:
    return os.getenv("FRIDAY_VERBOSE_PROVIDER_LOGS", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def configure_runtime_logging() -> None:
    log_path = _runtime_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    for logger_name in QUIET_LOGGERS:
        logger = logging.getLogger(logger_name)
        if any(getattr(handler, "_friday_runtime_handler", False) for handler in logger.handlers):
            continue

        logger.setLevel(logging.WARNING)
        logger.propagate = False

        console = logging.StreamHandler()
        console.setLevel(logging.WARNING)
        console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        if not _is_verbose():
            console.addFilter(RuntimeConsoleNoiseFilter())
        console._friday_runtime_handler = True  # type: ignore[attr-defined]
        logger.addHandler(console)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
            delay=True,
        )
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        file_handler._friday_runtime_handler = True  # type: ignore[attr-defined]
        logger.addHandler(file_handler)
