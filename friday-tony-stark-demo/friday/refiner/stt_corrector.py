from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from friday.prompts import build_stt_refiner_prompt

from .custom_vocab import (
    VocabularyProfile,
    build_vocabulary_context_text,
    default_vocabulary_profile,
    merge_vocabulary,
    normalize_with_aliases,
)

logger = logging.getLogger("friday-refiner")


@dataclass(slots=True)
class CorrectionResult:
    raw_text: str
    normalized_text: str
    refined_text: str
    provider: str
    fallback_used: bool
    error: str | None = None


class LLMRefinerProvider(Protocol):
    name: str

    def refine(self, *, prompt: str, timeout_seconds: float) -> str:
        raise NotImplementedError


class GroqRefinerProvider:
    name = "groq"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def refine(self, *, prompt: str, timeout_seconds: float) -> str:
        return _call_openai_compatible_chat(
            endpoint=self.endpoint,
            api_key=self.api_key,
            model=self.model,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
        )


class OpenAIRefinerProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://api.openai.com/v1/chat/completions"

    def refine(self, *, prompt: str, timeout_seconds: float) -> str:
        return _call_openai_compatible_chat(
            endpoint=self.endpoint,
            api_key=self.api_key,
            model=self.model,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
        )


def _call_openai_compatible_chat(
    *,
    endpoint: str,
    api_key: str,
    model: str,
    prompt: str,
    timeout_seconds: float,
) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You correct English STT transcripts without answering them."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 120,
    }
    request = Request(
        url=endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        raw_body = response.read().decode("utf-8")
    body = json.loads(raw_body)
    choices = body.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    content = message.get("content", "")
    return str(content or "").strip()


class STTCorrector:
    """
    Correct raw STT transcript safely with LLM + multi-stage fallback.
    """

    def __init__(
        self,
        *,
        enabled: bool = True,
        provider_name: str = "groq",
        groq_api_key: str = "",
        groq_model: str = "llama-3.1-8b-instant",
        openai_api_key: str = "",
        timeout_seconds: float = 4.0,
        base_profile: VocabularyProfile | None = None,
    ) -> None:
        self.enabled = enabled
        self.provider_name = provider_name.strip().lower()
        self.timeout_seconds = timeout_seconds
        self.base_profile = base_profile or default_vocabulary_profile()
        self._providers = self._build_provider_chain(
            provider_name=self.provider_name,
            groq_api_key=groq_api_key,
            groq_model=groq_model,
            openai_api_key=openai_api_key,
        )

    def correct(
        self,
        raw_transcript: str,
        *,
        language: str = "en-US",
        conversation_hint: str = "",
        extra_keywords: list[str] | None = None,
        extra_aliases: dict[str, str] | None = None,
    ) -> CorrectionResult:
        raw_text = str(raw_transcript or "")
        normalized = self._normalize_text(raw_text)
        profile = merge_vocabulary(self.base_profile, extra_keywords, extra_aliases)
        normalized = normalize_with_aliases(normalized, profile)
        minimal_refined = self._rule_based_refine(normalized)

        if not normalized:
            return CorrectionResult(
                raw_text=raw_text,
                normalized_text=normalized,
                refined_text=normalized,
                provider="none",
                fallback_used=True,
                error=None,
            )

        if not self.enabled:
            return CorrectionResult(
                raw_text=raw_text,
                normalized_text=normalized,
                refined_text=minimal_refined or normalized,
                provider="disabled",
                fallback_used=True,
            )

        if not self._providers:
            return CorrectionResult(
                raw_text=raw_text,
                normalized_text=normalized,
                refined_text=minimal_refined or normalized,
                provider="none",
                fallback_used=True,
                error="provider_not_configured",
            )

        prompt = build_stt_refiner_prompt(
            raw_transcript=minimal_refined or normalized,
            language=language,
            conversation_hint=conversation_hint,
            custom_vocabulary=build_vocabulary_context_text(profile),
        )

        last_error: str | None = None
        for index, provider in enumerate(self._providers):
            try:
                refined = provider.refine(prompt=prompt, timeout_seconds=self.timeout_seconds)
                refined_clean = self._post_process_output(refined)
                if self._looks_like_chatbot_reply(refined_clean):
                    raise ValueError("chatbot_like_output")
                final_text = normalize_with_aliases(refined_clean or minimal_refined or normalized, profile)
                final_text = self._rule_based_refine(final_text)
                if not final_text:
                    raise ValueError("empty_refined_output")
                return CorrectionResult(
                    raw_text=raw_text,
                    normalized_text=normalized,
                    refined_text=final_text,
                    provider=provider.name,
                    fallback_used=index > 0,
                )
            except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as exc:
                logger.warning("STT refiner provider_failed=%s reason=%s", provider.name, exc.__class__.__name__)
                last_error = f"{provider.name}:{exc.__class__.__name__}"
                continue
            except Exception as exc:
                logger.warning("STT refiner provider_unexpected=%s reason=%s", provider.name, exc.__class__.__name__)
                last_error = f"{provider.name}:{exc.__class__.__name__}"
                continue

        fallback_text = minimal_refined or normalized
        return CorrectionResult(
            raw_text=raw_text,
            normalized_text=normalized,
            refined_text=fallback_text,
            provider="rule_based",
            fallback_used=True,
            error=last_error,
        )

    def _build_provider_chain(
        self,
        *,
        provider_name: str,
        groq_api_key: str,
        groq_model: str,
        openai_api_key: str,
    ) -> list[LLMRefinerProvider]:
        providers: list[LLMRefinerProvider] = []
        groq_ready = bool(groq_api_key.strip())
        openai_ready = bool(openai_api_key.strip())

        if provider_name == "openai":
            if openai_ready:
                providers.append(OpenAIRefinerProvider(api_key=openai_api_key.strip()))
            if groq_ready:
                providers.append(GroqRefinerProvider(api_key=groq_api_key.strip(), model=groq_model.strip()))
            return providers

        if provider_name == "groq":
            if groq_ready:
                providers.append(GroqRefinerProvider(api_key=groq_api_key.strip(), model=groq_model.strip()))
            if openai_ready:
                providers.append(OpenAIRefinerProvider(api_key=openai_api_key.strip()))
            return providers

        if groq_ready:
            providers.append(GroqRefinerProvider(api_key=groq_api_key.strip(), model=groq_model.strip()))
        if openai_ready:
            providers.append(OpenAIRefinerProvider(api_key=openai_api_key.strip()))
        return providers

    def _normalize_text(self, text: str) -> str:
        normalized = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
        normalized = re.sub(r"\s+", " ", normalized).strip()
        normalized = normalized.replace("“", '"').replace("”", '"')
        normalized = normalized.replace("‘", "'").replace("’", "'")
        normalized = normalized.replace("`", "")
        return normalized

    def _post_process_output(self, text: str) -> str:
        content = str(text or "").strip()
        if not content:
            return ""

        if "```" in content:
            chunks = [part.strip() for part in content.split("```") if part.strip()]
            content = chunks[0] if chunks else ""

        lines = [line.strip("-* \t") for line in content.splitlines() if line.strip()]
        content = lines[0] if lines else ""
        content = re.sub(r'^["\']+|["\']+$', "", content).strip()
        content = re.sub(r"(?i)^(corrected sentence|transcript|output)\s*[:：-]\s*", "", content).strip()
        content = re.sub(r"\s+", " ", content).strip()
        return content

    def _rule_based_refine(self, text: str) -> str:
        """
        Minimal deterministic cleanup for short English command-like utterances.
        """
        refined = str(text or "").strip()
        if not refined:
            return ""

        replacements = {
            r"(?i)\bfriday\b": "Friday",
        }
        for pattern, value in replacements.items():
            refined = re.sub(pattern, value, refined)

        refined = re.sub(r"(?i)^friday\s+", "Friday, ", refined)
        refined = re.sub(r"\s+", " ", refined).strip()

        if refined:
            refined = refined[0].upper() + refined[1:]

        question_words = ("what", "when", "where", "why", "who", "how", "can", "could", "would", "is", "are")
        lower_refined = refined.lower()
        ends_with_punctuation = bool(re.search(r"[.!?]$", refined))
        if not ends_with_punctuation and any(word in lower_refined for word in question_words):
            refined = f"{refined}?"
        return refined

    def _looks_like_chatbot_reply(self, text: str) -> bool:
        sample = str(text or "").strip().lower()
        if not sample:
            return True
        return sample.startswith("hello") or sample.startswith("i am") or sample.startswith("certainly")

    @staticmethod
    def usage_example() -> str:
        return (
            "from friday.refiner import STTCorrector\n\n"
            "corrector = STTCorrector(enabled=True, provider_name='groq', groq_api_key='...')\n"
            "result = corrector.correct('fridai what is the weather today', language='en-US')\n"
            "print(result.refined_text)"
        )

    @staticmethod
    def sample_input_output_examples() -> list[tuple[str, str]]:
        return [
            ("open the living room lights", "Open the living room lights"),
            ("turn on the bedroom fan", "Turn on the bedroom fan"),
            ("fridai what is the weather today", "Friday, what is the weather today?"),
            ("call my mother", "Call my mother"),
            ("turn off smart home", "Turn off Smart Home"),
        ]
