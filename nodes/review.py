"""Node2와 Node4의 permit/reject 출력 계약."""

from dataclasses import dataclass

from .common import validate_relative_text


REVIEW_VERDICTS = {"permit", "reject"}


@dataclass(frozen=True)
class ReviewDecision:
    """Node2와 Node4가 반환하는 permit/reject와 짧은 이유."""

    verdict: str
    reason: str

    def __post_init__(self):
        if self.verdict not in REVIEW_VERDICTS:
            raise ValueError(f"알 수 없는 검토 결정입니다: {self.verdict}")

        validate_relative_text(self.reason, "reason")
