from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ResponseSafetyPolicy:
    max_answer_chars: int = 8000

    def clean(self, text: str) -> str:
        answer = text.strip()
        if len(answer) > self.max_answer_chars:
            return answer[: self.max_answer_chars].rstrip() + "..."
        return answer

    def is_empty(self, text: str) -> bool:
        return not text.strip()
