from __future__ import annotations

import hashlib
import math
import re


class HashEmbeddingModel:
    """외부 의존성 없이 텍스트를 고정 길이 벡터로 바꾸는 로컬 임베딩 대체층."""

    def __init__(self, dimensions: int = 256, min_n: int = 2, max_n: int = 4) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be > 0")
        if min_n <= 0 or max_n < min_n:
            raise ValueError("invalid ngram range")
        self.dimensions = dimensions
        self.min_n = min_n
        self.max_n = max_n
        self.model_id = f"hash-ngram-{dimensions}-{min_n}-{max_n}"

    def embed(self, text: str) -> list[float]:
        """문자 n-gram hashing으로 텍스트 벡터를 만든다."""

        vector = [0.0 for _ in range(self.dimensions)]
        normalized = _normalize_text(text)
        for ngram in _char_ngrams(normalized, self.min_n, self.max_n):
            digest = hashlib.md5(ngram.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        return _l2_normalize(vector)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """이미 정규화된 벡터끼리 cosine similarity를 계산한다."""

    if len(left) != len(right):
        raise ValueError("vector dimensions do not match")
    return sum(a * b for a, b in zip(left, right))


def _normalize_text(text: str) -> str:
    """검색용 텍스트를 너무 과하지 않게 정규화한다."""

    lowered = text.lower()
    return re.sub(r"\s+", " ", lowered).strip()


def _char_ngrams(text: str, min_n: int, max_n: int) -> list[str]:
    """한국어/영어가 섞여도 작동하도록 문자 n-gram을 만든다."""

    if not text:
        return []
    compact = text.replace(" ", "_")
    ngrams: list[str] = []
    for n in range(min_n, max_n + 1):
        if len(compact) < n:
            continue
        for index in range(0, len(compact) - n + 1):
            ngrams.append(compact[index : index + n])
    return ngrams


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
