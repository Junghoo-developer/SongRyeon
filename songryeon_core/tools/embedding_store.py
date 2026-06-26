from __future__ import annotations

from dataclasses import asdict, dataclass

from songryeon_core.tools.document_loader import DocumentChunk, chunk_markdown_docs
from songryeon_core.tools.embedding_backend import HashEmbeddingBackend
from songryeon_core.tools.embedding_model import HashEmbeddingModel, cosine_similarity


@dataclass
class EmbeddedChunk:
    """문서 chunk와 그 임베딩 벡터를 묶은 항목."""

    chunk: DocumentChunk
    embedding: list[float]
    embedding_model_id: str


@dataclass
class SearchResult:
    """임베딩 검색 결과 하나."""

    result_id: str
    doc_id: str
    chunk_id: str
    score: float
    embedding_model_id: str
    text_preview: str


class EmbeddingIndex:
    """문서 chunk 임베딩을 메모리에 들고 유사도 검색을 수행한다."""

    def __init__(self, embedded_chunks: list[EmbeddedChunk], model: HashEmbeddingModel) -> None:
        self.embedded_chunks = embedded_chunks
        self.model = model
        self.index_id = f"embedding_index:{model.model_id}:{len(embedded_chunks)}"

    @classmethod
    def build(
        cls,
        root: str,
        *,
        model: HashEmbeddingModel | None = None,
        max_chars: int = 900,
        overlap_chars: int = 120,
    ) -> EmbeddingIndex:
        """문서 루트에서 chunk를 만들고 임베딩 인덱스를 생성한다."""

        embedding_model = model or HashEmbeddingBackend()
        embedded_chunks: list[EmbeddedChunk] = []
        for chunk in chunk_markdown_docs(
            root,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        ):
            embedded_chunks.append(
                EmbeddedChunk(
                    chunk=chunk,
                    embedding=embedding_model.embed(chunk.text),
                    embedding_model_id=embedding_model.model_id,
                )
            )
        return cls(embedded_chunks, embedding_model)

    def search(self, query: str, *, top_k: int = 5) -> list[SearchResult]:
        """질의를 임베딩하고 가장 가까운 chunk들을 돌려준다."""

        if top_k <= 0:
            raise ValueError("top_k must be > 0")
        query_embedding = self.model.embed(query)
        scored: list[tuple[float, EmbeddedChunk]] = []
        for embedded in self.embedded_chunks:
            score = cosine_similarity(query_embedding, embedded.embedding)
            scored.append((score, embedded))
        scored.sort(key=lambda item: item[0], reverse=True)

        results: list[SearchResult] = []
        for index, (score, embedded) in enumerate(scored[:top_k], start=1):
            chunk = embedded.chunk
            preview = " ".join(chunk.text.split())
            results.append(
                SearchResult(
                    result_id=f"search_result_{index:04d}",
                    doc_id=chunk.doc_id,
                    chunk_id=chunk.chunk_id,
                    score=round(score, 6),
                    embedding_model_id=embedded.embedding_model_id,
                    text_preview=preview[:240],
                )
            )
        return results

    def to_records(self) -> list[dict[str, object]]:
        """디버깅용으로 인덱스 항목을 기본 자료형 목록으로 바꾼다."""

        return [asdict(item) for item in self.embedded_chunks]
