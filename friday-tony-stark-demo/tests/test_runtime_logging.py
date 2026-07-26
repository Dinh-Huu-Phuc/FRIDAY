from __future__ import annotations

import logging

from friday.src.common.runtime_logging import RuntimeConsoleNoiseFilter


def _record(message: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="livekit.agents",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def test_runtime_filter_hides_expected_provider_retry_noise() -> None:
    noise_filter = RuntimeConsoleNoiseFilter()

    assert not noise_filter.filter(
        _record("failed to synthesize speech: Connection error., retrying in 0.1s")
    )
    assert not noise_filter.filter(
        _record("AudioByteStream: incomplete frame during flush, dropping")
    )
    assert not noise_filter.filter(
        _record("STT refiner provider_failed=groq reason=HTTPError")
    )


def test_runtime_filter_keeps_actionable_warnings() -> None:
    assert RuntimeConsoleNoiseFilter().filter(
        _record("Microphone device was disconnected")
    )
