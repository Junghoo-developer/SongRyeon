"""Ollama가 각 노드의 JSON 형식을 지키도록 전달할 JSON Schema."""

from .common import MAX_REVIEW_CHARACTERS


_SHORT_TEXT_SCHEMA = {
    "type": "string",
    "minLength": 1,
    "maxLength": MAX_REVIEW_CHARACTERS,
}

NODE1_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["use_tool", "route_node2"],
        },
        "reason": _SHORT_TEXT_SCHEMA,
        "tool_name": {
            "type": ["string", "null"],
            "minLength": 1,
        },
        "arguments": {
            "type": ["object", "null"],
        },
    },
    "required": [
        "action",
        "reason",
        "tool_name",
        "arguments",
    ],
    "additionalProperties": False,
}


def _retention_schema(modes):
    """허용할 보존 방식만 다른 동일한 retention schema를 만든다."""

    return {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": list(modes),
            },
            "review": _SHORT_TEXT_SCHEMA,
            "start": {
                "type": ["integer", "null"],
            },
            "end": {
                "type": ["integer", "null"],
            },
        },
        "required": [
            "mode",
            "review",
            "start",
            "end",
        ],
        "additionalProperties": False,
    }


_RETENTION_SCHEMA = _retention_schema(
    ["full", "excerpt", "omit"]
)

NODE1_TOOL_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "retention": _RETENTION_SCHEMA,
        "next_action": NODE1_ACTION_SCHEMA,
    },
    "required": [
        "retention",
        "next_action",
    ],
    "additionalProperties": False,
}

NODE1_RECOVERY_CHOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "candidate_number": {
            "type": "integer",
            "minimum": 1,
        },
    },
    "required": ["candidate_number"],
    "additionalProperties": False,
}

NODE1_RECOVERY_RETENTION_SCHEMA = _retention_schema(
    ["full", "excerpt"]
)

def _validated_chunk_ids(chunk_ids):
    """동적 enum에 넣을 중복 없는 청크 ID를 검증한다."""

    if not isinstance(chunk_ids, (list, tuple)) or not chunk_ids:
        raise ValueError("긴 원문 스키마에는 chunk_ids가 필요합니다.")

    if any(
        not isinstance(chunk_id, str) or not chunk_id
        for chunk_id in chunk_ids
    ):
        raise ValueError("모든 chunk_id는 비어 있지 않은 문자열이어야 합니다.")

    if len(set(chunk_ids)) != len(chunk_ids):
        raise ValueError("chunk_ids는 중복될 수 없습니다.")

    return list(chunk_ids)


def _chunk_retention_schema(chunk_ids, *, allow_omit):
    """긴 원문에서 문자 위치 대신 청크 ID를 고르는 schema를 만든다."""

    validated_ids = _validated_chunk_ids(chunk_ids)
    modes = ["chunk", "omit"] if allow_omit else ["chunk"]
    chunk_id_values = (
        [*validated_ids, None]
        if allow_omit
        else validated_ids
    )
    chunk_id_type = (
        ["string", "null"]
        if allow_omit
        else "string"
    )
    return {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": modes,
            },
            "review": _SHORT_TEXT_SCHEMA,
            "chunk_id": {
                "type": chunk_id_type,
                "enum": chunk_id_values,
            },
        },
        "required": [
            "mode",
            "review",
            "chunk_id",
        ],
        "additionalProperties": False,
    }


def node1_tool_decision_schema(*, allow_full, chunk_ids=None):
    """짧은 원문은 기존 계약, 긴 원문은 청크 선택 계약을 반환한다."""

    if not isinstance(allow_full, bool):
        raise TypeError("allow_full은 bool이어야 합니다.")

    if allow_full:
        return NODE1_TOOL_DECISION_SCHEMA

    return {
        "type": "object",
        "properties": {
            "retention": _chunk_retention_schema(
                chunk_ids,
                allow_omit=True,
            ),
            "next_action": NODE1_ACTION_SCHEMA,
        },
        "required": [
            "retention",
            "next_action",
        ],
        "additionalProperties": False,
    }


def node1_recovery_retention_schema(*, allow_full, chunk_ids=None):
    """짧은 복구는 기존 계약, 긴 복구는 청크 선택 계약을 반환한다."""

    if not isinstance(allow_full, bool):
        raise TypeError("allow_full은 bool이어야 합니다.")

    if allow_full:
        return NODE1_RECOVERY_RETENTION_SCHEMA

    return _chunk_retention_schema(
        chunk_ids,
        allow_omit=False,
    )


REVIEW_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["permit", "reject"],
        },
        "reason": _SHORT_TEXT_SCHEMA,
    },
    "required": [
        "verdict",
        "reason",
    ],
    "additionalProperties": False,
}

NODE3_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "minLength": 1,
            # Ollama 0.32.4는 큰 maxLength를 grammar로 만들 때 실패할 수 있다.
            # 실제 2,400자 상한은 아래 schema와 별개로 Node3Answer가 검사한다.
        },
    },
    "required": ["answer"],
    "additionalProperties": False,
}
