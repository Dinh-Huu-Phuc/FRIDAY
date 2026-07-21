from __future__ import annotations

import os
from dataclasses import dataclass
from typing import AsyncIterator, Protocol

import httpx

from ..schemas.llm_entities import ChatMessage, LLMRequest, LLMResponse


class LLMClient(Protocol):
    async def complete(self, request: LLMRequest) -> LLMResponse:
        ...

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        ...


@dataclass(slots=True)
class OpenAICompatibleChatClient:
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    provider: str = "openai-compatible"
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("FRIDAY_LLM_API_KEY")
        self.base_url = os.getenv("FRIDAY_LLM_BASE_URL", self.base_url).rstrip("/")

    async def complete(self, request: LLMRequest) -> LLMResponse:
        payload = self._payload(request, stream=False)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(self._chat_url(), headers=self._headers(), json=payload)
            response.raise_for_status()
        raw = response.json()
        content = str(raw.get("choices", [{}])[0].get("message", {}).get("content", ""))
        return LLMResponse(content=content, model=request.model, provider=self.provider, raw=raw)

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        payload = self._payload(request, stream=True)
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", self._chat_url(), headers=self._headers(), json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if data == "[DONE]":
                        break
                    try:
                        import json

                        raw = json.loads(data)
                    except Exception:
                        continue
                    delta = raw.get("choices", [{}])[0].get("delta", {})
                    token = str(delta.get("content") or "")
                    if token:
                        yield token

    def _payload(self, request: LLMRequest, *, stream: bool) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": request.model,
            "messages": [message.to_dict() for message in request.messages],
            "temperature": request.temperature,
            "stream": stream,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        return payload

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _chat_url(self) -> str:
        return f"{self.base_url}/chat/completions"


@dataclass(slots=True)
class StaticLLMClient:
    content: str = "I need an LLM client configuration before I can answer with the model."
    provider: str = "static"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content=self.content, model=request.model, provider=self.provider)

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        for token in self.content.split(" "):
            yield token + " "
