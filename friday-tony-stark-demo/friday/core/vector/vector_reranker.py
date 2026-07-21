from __future__ import annotations

from dataclasses import dataclass

from .vector_schemas import VectorSearchResult


@dataclass(slots=True)
class KeywordOverlapReranker:
    weight_overlap: float = 0.3

    def rerank(self, query: str, candidates: list[VectorSearchResult]) -> list[VectorSearchResult]:
        query_terms = {term for term in query.lower().split() if term}
        rescored = []
        for item in candidates:
            overlap = 0
            if query_terms:
                text_terms = set(item.chunk.text.lower().split())
                overlap = len(query_terms & text_terms)
            rerank_score = item.score + self.weight_overlap * overlap
            item.rerank_score = rerank_score
            rescored.append(item)
        rescored.sort(key=lambda row: row.rerank_score if row.rerank_score is not None else row.score, reverse=True)
        return rescored
