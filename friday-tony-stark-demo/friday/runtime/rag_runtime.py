from __future__ import annotations

from dataclasses import dataclass

from friday.app.realtime.system_socket_channels import SystemSocketChannel
from friday.core.llm.responder import RAGResponder
from friday.core.rag.rag_prompt_builder import build_rag_prompt_context
from friday.core.vector.vector_reranker import KeywordOverlapReranker
from friday.core.vector.vector_retriever import VectorRetriever
from friday.core.vector.vector_schemas import VectorSearchResult

from .retrieval_context import RetrievalContext
from .system_socket_event_types import SystemSocketEventType
from .system_socket_publishers import RuntimeSystemSocketPublisher


@dataclass(slots=True)
class RuntimeRAGAnswer:
    answer: str
    retrieval_context: RetrievalContext
    sources: list[dict[str, object]]


@dataclass(slots=True)
class RagRuntime:
    retriever: VectorRetriever
    responder: RAGResponder
    reranker: KeywordOverlapReranker | None = None
    publisher: RuntimeSystemSocketPublisher | None = None
    top_k: int = 5
    prompt_max_chars: int = 3200

    async def answer(self, query: str, *, stream: bool = False) -> RuntimeRAGAnswer:
        await self._publish(SystemSocketEventType.RAG_RETRIEVAL_STARTED, {"query": query})
        retrieved = self.retriever.retrieve(query, top_k=self.top_k)
        chunks = self._rerank(query, retrieved)
        await self._publish(SystemSocketEventType.RAG_CHUNKS_READY, {"chunks": [item.to_dict() for item in chunks]})

        prompt_context = build_rag_prompt_context(chunks, max_chars=self.prompt_max_chars)
        await self._publish(
            SystemSocketEventType.RAG_RETRIEVAL_COMPLETED,
            {"query": query, "top_k": self.top_k, "result_count": len(chunks)},
        )

        await self._publish(SystemSocketEventType.LLM_RESPONSE_STARTED, {"query": query})
        if stream:
            answer_parts: list[str] = []
            async for token in self.responder.stream_answer(question=query, rag_context=prompt_context):
                answer_parts.append(token)
                await self._publish(SystemSocketEventType.LLM_RESPONSE_TOKEN, {"token": token})
            answer = "".join(answer_parts).strip()
        else:
            answer = await self.responder.answer(question=query, rag_context=prompt_context)

        await self._publish(SystemSocketEventType.LLM_RESPONSE_COMPLETED, {"answer": answer})
        return RuntimeRAGAnswer(
            answer=answer,
            retrieval_context=RetrievalContext(query=query, chunks=chunks, prompt_context=prompt_context),
            sources=[self._source_payload(item) for item in chunks],
        )

    def _rerank(self, query: str, chunks: list[VectorSearchResult]) -> list[VectorSearchResult]:
        if self.reranker is None:
            return chunks
        return self.reranker.rerank(query, chunks)

    async def _publish(self, event_type: SystemSocketEventType, payload: dict[str, object]) -> None:
        if self.publisher is None:
            return
        await self.publisher.publish(event_type, channel=SystemSocketChannel.RAG, payload=payload)

    def _source_payload(self, item: VectorSearchResult) -> dict[str, object]:
        return {
            "id": item.chunk.id,
            "chunk_id": item.chunk.chunk_id,
            "title": item.chunk.title,
            "source_path": item.chunk.source_path,
            "source_type": item.chunk.source_type,
            "tags": item.chunk.tags,
            "score": item.rerank_score if item.rerank_score is not None else item.score,
        }
