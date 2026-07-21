from __future__ import annotations

from enum import StrEnum


class SystemSocketEventType(StrEnum):
    RAG_RETRIEVAL_STARTED = "rag_retrieval_started"
    RAG_RETRIEVAL_COMPLETED = "rag_retrieval_completed"
    RAG_CHUNKS_READY = "rag_chunks_ready"
    LLM_RESPONSE_STARTED = "llm_response_started"
    LLM_RESPONSE_TOKEN = "llm_response_token"
    LLM_RESPONSE_COMPLETED = "llm_response_completed"
    RUNTIME_UPDATED = "runtime_updated"
    ERROR = "error"
