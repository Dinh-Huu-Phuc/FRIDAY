from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from friday.src.services.agent.stt_service import (
    SpeechTranscriptionError,
    _apply_intent_aliases,
    _is_stt_instruction_echo,
    transcribe_core_audio,
)


def test_power_aliases_are_corrected_inside_a_complete_transcript() -> None:
    assert _apply_intent_aliases("Firday, wake up.") == "FRIDAY, wake up."
    assert _apply_intent_aliases("f r i d a y online") == "FRIDAY online"


def test_stt_instruction_echo_is_detected_without_blocking_real_commands() -> None:
    assert _is_stt_instruction_echo(
        "Friday, voice assistant commands may include: Friday, wake up; "
        "wake up, Friday; Friday, sleep; Friday, online."
    )
    assert not _is_stt_instruction_echo("Friday, wake up.")


def test_allowlisted_power_transcript_skips_the_llm_refiner() -> None:
    response = Mock(status_code=200)
    response.json.return_value = {"text": "Firday, wake up."}
    client = AsyncMock()
    client.post.return_value = response
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False

    with (
        patch(
            "friday.src.services.agent.stt_service.httpx.AsyncClient",
            return_value=client,
        ),
        patch(
            "friday.src.services.agent.stt_service._resolve_openai_api_key",
            return_value="test-key",
        ),
        patch("friday.src.services.agent.stt_service._build_corrector") as corrector,
    ):
        result = asyncio.run(
            transcribe_core_audio(
                b"webm-audio",
                content_type="audio/webm;codecs=opus",
                language="en",
            )
        )

    assert result.refined_text == "FRIDAY, wake up."
    assert result.refiner_provider == "power-command"
    corrector.assert_not_called()
    assert "prompt" not in client.post.call_args.kwargs["data"]


def test_instruction_echo_is_rejected_before_it_reaches_chat() -> None:
    response = Mock(status_code=200)
    response.json.return_value = {
        "text": (
            "Friday, voice assistant commands may include: Friday, wake up; "
            "wake up, Friday; Friday, sleep; Friday, online."
        )
    }
    client = AsyncMock()
    client.post.return_value = response
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False

    with (
        patch(
            "friday.src.services.agent.stt_service.httpx.AsyncClient",
            return_value=client,
        ),
        patch(
            "friday.src.services.agent.stt_service._resolve_openai_api_key",
            return_value="test-key",
        ),
        pytest.raises(SpeechTranscriptionError, match="instruction text"),
    ):
        asyncio.run(
            transcribe_core_audio(
                b"near-silent-webm-audio",
                content_type="audio/webm;codecs=opus",
                language="en",
            )
        )
