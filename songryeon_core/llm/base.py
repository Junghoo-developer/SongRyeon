from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LLMRequest:
    """LLM 호출에 필요한 최소 입력."""

    prompt: str
    input_payload: dict[str, object] = field(default_factory=dict)
    response_format: str = "json"


@dataclass
class LLMResponse:
    """LLM 호출 결과."""

    text: str
    model_id: str
    raw: object | None = None


class LLMAdapter(Protocol):
    """로컬/원격 LLM adapter가 지켜야 하는 최소 인터페이스."""

    model_id: str

    def complete(self, request: LLMRequest) -> LLMResponse:
        """요청을 받아 응답 텍스트를 돌려준다."""
