from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ResponsePolicy:
    high_entropy_threshold: float = 1.4

    def choose_tone(self, entropy: float) -> str:
        if entropy >= self.high_entropy_threshold:
            return "cautious"
        return "grounded"
