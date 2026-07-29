"""모든 도구 원문을 생략했을 때 Node1이 복구할 후보를 고른다."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Node1RecoveryChoice:
    """공개할 원문을 다시 고르는 Node1의 상대 판단."""

    candidate_number: int

    def __post_init__(self):
        if (
            not isinstance(self.candidate_number, int)
            or isinstance(self.candidate_number, bool)
            or self.candidate_number < 1
        ):
            raise ValueError("candidate_number는 1 이상의 정수여야 합니다.")
