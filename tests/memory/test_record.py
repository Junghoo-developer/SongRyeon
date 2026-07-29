"""원본 기억 한 줄의 7필드 생성 규칙을 검사한다."""

from datetime import datetime
from uuid import UUID

import pytest

from memory.record import create_information_record


def test_create_absolute_record():
    record = create_information_record(
        "도구를 사용했다.",
        "absolute",
        "action",
        "turn-1",
    )

    assert record["information"] == "도구를 사용했다."
    assert record["information_class"] == "absolute"
    assert record["code_verifiable"] is True
    assert record["information_type"] == "action"
    assert record["turn_id"] == "turn-1"

    # 문자열 모양만 확인하지 않고 실제 UUID와 시각으로 해석되는지 검사한다.
    UUID(record["information_id"])
    created_at = datetime.fromisoformat(record["created_at"])
    assert created_at.tzinfo is not None


def test_invalid_information_class():
    with pytest.raises(ValueError):
        create_information_record(
            "테스트",
            "unknown",
            "test",
            "turn-1",
        )


def test_create_relative_record_is_not_code_verifiable():
    record = create_information_record(
        "노드가 이 정보면 충분하다고 판단했다.",
        "relative",
        "review",
        "turn-2",
    )

    assert record["information_class"] == "relative"
    assert record["code_verifiable"] is False
