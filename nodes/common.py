"""모든 노드의 짧은 자연어 이유가 공유하는 검증 규칙."""


MAX_REVIEW_CHARACTERS = 500


def validate_short_reason(value, field_name):
    """다음 노드가 볼 짧은 판단인지 확인하되 원문은 수정하지 않는다."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name}에는 짧은 이유가 필요합니다.")

    if len(value) > MAX_REVIEW_CHARACTERS:
        raise ValueError(
            f"{field_name}은 {MAX_REVIEW_CHARACTERS}자를 넘을 수 없습니다."
        )
