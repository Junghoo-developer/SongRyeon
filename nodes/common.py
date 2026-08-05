"""모든 노드의 자연어 R이 공유하는 최소 검증 규칙."""


def validate_relative_text(value, field_name):
    """프롬프트가 길이를 유도하게 두고 비어 있지 않은 문자열만 검사한다."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name}에는 비어 있지 않은 문자열이 필요합니다.")
