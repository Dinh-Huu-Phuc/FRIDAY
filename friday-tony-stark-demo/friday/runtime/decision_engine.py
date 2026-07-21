from __future__ import annotations

from dataclasses import dataclass

from ..core.rag import KeywordOverlapReranker, RagRetriever, build_rag_prompt_context
from ..language import LanguageManager, detect_language_switch
from .memory_runtime import RuntimeMemory
from .response_policy import ResponsePolicy
from .scorer import RuntimeScorer


@dataclass(slots=True)
class RuntimeDecisionEngine:
    retriever: RagRetriever
    language_manager: LanguageManager
    memory: RuntimeMemory
    scorer: RuntimeScorer
    response_policy: ResponsePolicy
    reranker: KeywordOverlapReranker | None = None

    def process_user_input(
        self,
        *,
        session_id: str,
        user_input: str,
        emotion_vector: dict[str, float],
        top_k: int = 5,
    ) -> dict[str, object]:
        state = self.memory.get_or_create(session_id)

        detection = detect_language_switch(user_input)
        if detection.should_switch and detection.language:
            state.current_language = detection.language

        retrieved = self.retriever.retrieve(user_input, top_k=top_k)
        if self.reranker is not None:
            retrieved = self.reranker.rerank(user_input, retrieved)

        prompt_context = build_rag_prompt_context(retrieved)
        session_mood = self.scorer.update_session_mood(state.session_mood, emotion_vector)
        entropy_value = self.scorer.compute_entropy(emotion_vector)
        fused_state = self.scorer.compute_fused_state(
            current_emotion=emotion_vector,
            session_mood=session_mood,
            user_style_projection=state.user_style_projection,
        )
        tone = self.response_policy.choose_tone(entropy_value)
        state.session_mood = session_mood

        return {
            "language": state.current_language,
            "language_switched": detection.should_switch,
            "prompt_context": prompt_context,
            "retrieved_chunks": [
                {
                    "chunk_id": row.chunk.chunk_id,
                    "source_path": row.chunk.source_path,
                    "source_type": row.chunk.source_type,
                    "score": row.score,
                    "rerank_score": row.rerank_score,
                }
                for row in retrieved
            ],
            "session_mood": session_mood,
            "fused_state": fused_state,
            "entropy": entropy_value,
            "tone": tone,
            "system_message": self.language_manager.get("system.retrieval_ready", language=state.current_language),
        }
