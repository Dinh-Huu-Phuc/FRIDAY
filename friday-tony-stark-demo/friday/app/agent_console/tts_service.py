from __future__ import annotations

import os
from collections import OrderedDict
from functools import lru_cache

from friday.googleServiceCloud.credentials import ensure_google_application_credentials
from livekit.plugins import deepgram, google as lk_google, openai as lk_openai, sarvam

DEFAULT_TTS_PROVIDER = os.getenv("PAGECLIENT_TTS_PROVIDER", os.getenv("TTS_PROVIDER", "sarvam")).strip().lower()
DEFAULT_TTS_SPEED = float(os.getenv("PAGECLIENT_TTS_SPEED", os.getenv("TTS_SPEED", "1.15")))
_AUDIO_CACHE: OrderedDict[tuple[str, str], bytes] = OrderedDict()
_AUDIO_CACHE_LIMIT = 16


def _resolve_provider(provider: str) -> str:
    selected = (provider or "auto").strip().lower()
    if selected == "auto":
        selected = DEFAULT_TTS_PROVIDER or "openai"
    return selected


@lru_cache(maxsize=8)
def _build_tts(provider: str):
    selected = _resolve_provider(provider)

    if selected == "deepgram":
        return deepgram.TTS(
            model=os.getenv("DEEPGRAM_TTS_MODEL", "aura-2-andromeda-en"),
            sample_rate=int(os.getenv("DEEPGRAM_TTS_SAMPLE_RATE", "24000")),
            api_key=os.getenv("DEEPGRAM_API_KEY") or None,
        )

    if selected == "google":
        credentials_file = ensure_google_application_credentials()
        return lk_google.TTS(
            language=os.getenv("GOOGLE_TTS_LANGUAGE", "en-US"),
            voice_name=os.getenv("GOOGLE_TTS_VOICE_NAME", "en-US-Wavenet-F"),
            sample_rate=int(os.getenv("GOOGLE_TTS_SAMPLE_RATE", "24000")),
            speaking_rate=float(os.getenv("GOOGLE_TTS_SPEAKING_RATE", str(DEFAULT_TTS_SPEED))),
            credentials_file=credentials_file,
        )

    if selected == "sarvam":
        return sarvam.TTS(
            target_language_code=os.getenv("SARVAM_TTS_LANGUAGE", "en-IN"),
            model=os.getenv("SARVAM_TTS_MODEL", "bulbul:v3"),
            speaker=os.getenv("SARVAM_TTS_SPEAKER", "priya"),
            pace=DEFAULT_TTS_SPEED,
            api_key=os.getenv("SARVAM_API_KEY") or None,
        )

    if selected == "openai":
        return lk_openai.TTS(
            model=os.getenv("OPENAI_TTS_MODEL", "tts-1"),
            voice=os.getenv("OPENAI_TTS_VOICE", "nova"),
            speed=DEFAULT_TTS_SPEED,
            api_key=os.getenv("OPENAI_API_KEY") or None,
            response_format=os.getenv("OPENAI_TTS_RESPONSE_FORMAT", "pcm"),
        )

    raise ValueError(f"Unsupported TTS provider: {provider!r}")


async def synthesize_console_speech(text: str, *, provider: str = "auto") -> bytes:
    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("TTS text must not be empty.")

    selected_provider = _resolve_provider(provider)
    cache_key = (selected_provider, normalized_text)
    cached = _AUDIO_CACHE.get(cache_key)
    if cached is not None:
        _AUDIO_CACHE.move_to_end(cache_key)
        return cached

    tts = _build_tts(selected_provider)
    audio_frame = await tts.synthesize(normalized_text).collect()
    audio = audio_frame.to_wav_bytes()
    if len(normalized_text) <= 240:
        _AUDIO_CACHE[cache_key] = audio
        _AUDIO_CACHE.move_to_end(cache_key)
        while len(_AUDIO_CACHE) > _AUDIO_CACHE_LIMIT:
            _AUDIO_CACHE.popitem(last=False)
    return audio

