"""도구·노드 감사 기록이 함께 사용하는 작은 생성·검증 함수."""

import json
import sys

from .agent_view import format_agent_memory
from .record import create_information_record
from .settings import (
    AGENT_VISIBLE_FIELDS,
    HIDDEN_INFORMATION_TYPE_PREFIXES,
)


def canonical_json(value):
    """같은 코드 사실이 항상 같은 짧은 JSON 문자열이 되게 한다."""

    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (RecursionError, TypeError, ValueError) as error:
        raise ValueError(
            "감사 기록 값은 정렬 가능한 일반 JSON이어야 합니다."
        ) from error


def new_audit_record(
    information,
    information_class,
    information_type,
    turn_id,
):
    """감사 정보 하나를 기존 7필드 원자 기록으로 만든다."""

    return create_information_record(
        information=information,
        information_class=information_class,
        information_type=information_type,
        turn_id=turn_id,
    )


def validate_visible_batch(records, max_characters):
    """새 공개 묶음 전체가 한 번에 공통 시야 예산에 들어오는지 확인한다."""

    visible_records = [
        {
            "memory_index": sys.maxsize,
            **{
                field: record[field]
                for field in AGENT_VISIBLE_FIELDS
            },
        }
        for record in records
        if not record["information_type"].startswith(
            HIDDEN_INFORMATION_TYPE_PREFIXES
        )
    ]
    rendered = format_agent_memory(visible_records)

    if len(rendered) > max_characters:
        raise ValueError(
            "선택한 본문과 검토 기록이 에이전트 시야 예산을 초과합니다. "
            "더 작은 excerpt·chunk 또는 omit이 필요합니다."
        )
