"""Node3가 반환하는 최종 답변 후보의 출력 계약."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Node3Answer:
    """Node4가 검토하고 최종 사용자에게 전달할 Node3의 답변 후보."""

    answer: str

    def __post_init__(self):
        if not isinstance(self.answer, str) or not self.answer.strip():
            raise ValueError("answer는 비어 있지 않은 문자열이어야 합니다.")
