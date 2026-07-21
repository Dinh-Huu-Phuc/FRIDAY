from __future__ import annotations

from ..schemas.llm_entities import ChatMessage


DEFAULT_RAG_SYSTEM_PROMPT = (
    "You are F.R.I.D.A.Y., a precise assistant. Answer from the retrieved context when it is relevant. "
    "If the context is insufficient, say what is missing. Keep citations in the answer when sources are provided."
)


def build_grounded_messages(
    *,
    question: str,
    rag_context: str,
    system_prompt: str = DEFAULT_RAG_SYSTEM_PROMPT,
) -> list[ChatMessage]:
    user_content = f"Question:\n{question.strip()}\n\n"
    if rag_context.strip():
        user_content += f"{rag_context.strip()}\n\nUse the retrieved context and cite sources like [1] when useful."
    else:
        user_content += "No retrieved context was available. Answer only if you can do so safely without inventing facts."
    return [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=user_content),
    ]
