from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator

from ..schemas.llm_entities import LLMRequest
from .client import LLMClient
from .prompts import DEFAULT_RAG_SYSTEM_PROMPT, build_grounded_messages
from .safety import ResponseSafetyPolicy


@dataclass(slots=True)
class RAGResponder:
    client: LLMClient
    model: str = "gpt-4o-mini"
    system_prompt: str = DEFAULT_RAG_SYSTEM_PROMPT
    temperature: float = 0.2
    safety_policy: ResponseSafetyPolicy | None = None

    def __post_init__(self) -> None:
        if self.safety_policy is None:
            self.safety_policy = ResponseSafetyPolicy()

    async def answer(self, *, question: str, rag_context: str) -> str:
        request = LLMRequest(
            messages=build_grounded_messages(question=question, rag_context=rag_context, system_prompt=self.system_prompt),
            model=self.model,
            temperature=self.temperature,
        )
        response = await self.client.complete(request)
        return self.safety_policy.clean(response.content)

    async def stream_answer(self, *, question: str, rag_context: str) -> AsyncIterator[str]:
        request = LLMRequest(
            messages=build_grounded_messages(question=question, rag_context=rag_context, system_prompt=self.system_prompt),
            model=self.model,
            temperature=self.temperature,
            stream=True,
        )
        async for token in self.client.stream(request):
            yield token
