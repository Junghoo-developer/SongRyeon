"""Ollama가 각 노드의 JSON 형식을 지키도록 전달할 JSON Schema."""


_RELATIVE_TEXT_SCHEMA = {
    "type": "string",
    "minLength": 1,
}

NODE1_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["use_tool", "route_node2"],
        },
        "reason": _RELATIVE_TEXT_SCHEMA,
        "tool_name": {
            "type": ["string", "null"],
            "minLength": 1,
        },
        "arguments": {
            # OpenAI strict structured output은 모든 object 분기에
            # additionalProperties=False가 필요하다. 현재 Node1이 쓸 수 있는
            # 두 도구의 실제 인자 계약만 명시해 임의 객체 생성을 막는다.
            "anyOf": [
                {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
                {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "minLength": 1,
                        },
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
                {
                    "type": "null",
                },
            ],
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
    """보존 방식마다 허용되는 위치 값까지 구분한 retention schema를 만든다.

    mode와 start/end를 서로 독립적인 nullable 필드로 두면 모델이
    ``full + start=0``처럼 각 필드의 형식은 맞지만 조합은 틀린 JSON을 만들
    수 있다. 서로 겹치지 않는 anyOf 분기로 조합 자체를 제한한다.
    """

    variants = []

    for mode in modes:
        uses_positions = mode == "excerpt"
        variants.append(
            {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": [mode],
                    },
                    "review": _RELATIVE_TEXT_SCHEMA,
                    "start": {
                        "type": "integer" if uses_positions else "null",
                    },
                    "end": {
                        "type": "integer" if uses_positions else "null",
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
        )

    return {
        "anyOf": variants,
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


def _retention_response_schema(retention_schema):
    """응답 루트를 object로 유지하면서 조건부 retention을 감싼다."""

    return {
        "type": "object",
        "properties": {
            "retention": retention_schema,
        },
        "required": ["retention"],
        "additionalProperties": False,
    }


NODE1_RECOVERY_RETENTION_SCHEMA = _retention_response_schema(
    _retention_schema(["full", "excerpt"])
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
    chunk_variant = {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["chunk"],
            },
            "review": _RELATIVE_TEXT_SCHEMA,
            "chunk_id": {
                "type": "string",
                "enum": validated_ids,
            },
        },
        "required": [
            "mode",
            "review",
            "chunk_id",
        ],
        "additionalProperties": False,
    }

    if not allow_omit:
        return chunk_variant

    omit_variant = {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["omit"],
            },
            "review": _RELATIVE_TEXT_SCHEMA,
            "chunk_id": {
                "type": "null",
            },
        },
        "required": [
            "mode",
            "review",
            "chunk_id",
        ],
        "additionalProperties": False,
    }
    return {
        "anyOf": [
            chunk_variant,
            omit_variant,
        ],
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

    return _retention_response_schema(
        _chunk_retention_schema(
            chunk_ids,
            allow_omit=False,
        )
    )


REVIEW_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        # 구조화 출력은 속성 선언 순서를 따라 생성된다. 짧은 근거를 먼저
        # 만들게 해야 모델이 판정을 출력한 뒤 reason에서 스스로 뒤집는
        # 모순을 줄일 수 있다.
        "reason": _RELATIVE_TEXT_SCHEMA,
        "verdict": {
            "type": "string",
            "enum": ["permit", "reject"],
        },
    },
    "required": [
        "reason",
        "verdict",
    ],
    "additionalProperties": False,
}

NODE3_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "minLength": 1,
        },
    },
    "required": ["answer"],
    "additionalProperties": False,
}
