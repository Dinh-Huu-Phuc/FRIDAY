from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def default_knowledge_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "knowledge"


@dataclass(slots=True)
class VectorConfig:
    knowledge_dir: Path = default_knowledge_dir()
    backend: str = "faiss"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimensions: int = 384
    normalize: bool = True
    top_k: int = 5

    @property
    def index_dir(self) -> Path:
        return self.knowledge_dir / "indexes" / "vector"

    @property
    def processed_dir(self) -> Path:
        return self.knowledge_dir / "processed"
