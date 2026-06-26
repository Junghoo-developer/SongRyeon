from __future__ import annotations

from typing import Protocol

from songryeon_core.tools.embedding_model import HashEmbeddingModel


class EmbeddingBackend(Protocol):
    """검색용 embedding backend 최소 인터페이스."""

    model_id: str
    dimensions: int

    def embed(self, text: str) -> list[float]:
        """텍스트를 벡터로 변환한다."""


class HashEmbeddingBackend:
    """기존 HashEmbeddingModel을 backend 인터페이스로 감싼다."""

    def __init__(self, dimensions: int = 256, min_n: int = 2, max_n: int = 4) -> None:
        self.model = HashEmbeddingModel(dimensions=dimensions, min_n=min_n, max_n=max_n)
        self.model_id = self.model.model_id
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        return self.model.embed(text)
