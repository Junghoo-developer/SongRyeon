"""LLM의 JSON 객체를 코드가 신뢰하는 노드 출력 계약으로 바꾼다.

파서는 값을 보정하거나 형변환하지 않는다. 키가 빠졌거나 추가됐거나 값이
계약과 다르면 해당 노드가 다시 판단할 수 있도록 명시적인 예외를 발생시킨다.
"""

from .actions import Node1Action, Node1ToolDecision
from .answer import Node3Answer
from .recovery import Node1RecoveryChoice
from .retention import (
    DEFAULT_CHUNK_CHARACTERS,
    RetentionDecision,
    select_retained_content,
)
from .review import ReviewDecision


DEFAULT_MAX_SELECTED_CHARACTERS = DEFAULT_CHUNK_CHARACTERS


def _require_exact_object(payload, required_keys, object_name):
    """일반 dict이고 키가 계약과 정확히 같은지 확인한다."""

    if not isinstance(payload, dict):
        raise ValueError(f"{object_name}은 JSON 객체여야 합니다.")

    actual_keys = set(payload)
    expected_keys = set(required_keys)

    if actual_keys != expected_keys:
        missing_keys = sorted(expected_keys - actual_keys)
        extra_keys = sorted(
            actual_keys - expected_keys,
            key=lambda value: repr(value),
        )
        details = []

        if missing_keys:
            details.append("누락: " + ", ".join(missing_keys))

        if extra_keys:
            details.append(
                "추가: "
                + ", ".join(str(key) for key in extra_keys)
            )

        raise ValueError(
            f"{object_name}의 키가 계약과 다릅니다"
            + (": " + "; ".join(details) if details else "")
            + "."
        )

    return payload


def _is_plain_positive_integer(value):
    """bool을 정수로 취급하지 않고 1 이상의 int만 허용한다."""

    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0
    )


def parse_node1_action(payload):
    """엄격한 JSON 객체를 ``Node1Action``으로 검증한다."""

    action = _require_exact_object(
        payload,
        {"action", "reason", "tool_name", "arguments"},
        "Node1Action",
    )
    return Node1Action(
        action=action["action"],
        reason=action["reason"],
        tool_name=action["tool_name"],
        arguments=action["arguments"],
    )


def parse_node1_tool_decision(
    payload,
    raw_text,
    max_selected_characters=DEFAULT_MAX_SELECTED_CHARACTERS,
):
    """Node1의 보존·다음 행동을 검증하고 선택 본문의 상한도 확인한다."""

    if not _is_plain_positive_integer(max_selected_characters):
        raise ValueError(
            "max_selected_characters는 1 이상의 정수여야 합니다."
        )

    decision_payload = _require_exact_object(
        payload,
        {"retention", "next_action"},
        "Node1ToolDecision",
    )
    retention = _parse_retention(
        decision_payload["retention"],
        raw_text,
        max_selected_characters,
        allow_omit=True,
    )

    next_action = parse_node1_action(decision_payload["next_action"])
    return Node1ToolDecision(
        retention=retention,
        next_action=next_action,
    )


def _parse_retention(
    payload,
    raw_text,
    max_selected_characters,
    *,
    allow_omit,
):
    """일반 보존과 omit 복구가 공유하는 정확한 원문 선택 검증."""

    uses_chunk_contract = len(raw_text) > max_selected_characters

    if uses_chunk_contract:
        retention_payload = _require_exact_object(
            payload,
            {"mode", "review", "chunk_id"},
            "RetentionDecision",
        )
        retention = RetentionDecision(
            mode=retention_payload["mode"],
            review=retention_payload["review"],
            chunk_id=retention_payload["chunk_id"],
        )
    else:
        retention_payload = _require_exact_object(
            payload,
            {"mode", "review", "start", "end"},
            "RetentionDecision",
        )
        retention = RetentionDecision(
            mode=retention_payload["mode"],
            review=retention_payload["review"],
            start=retention_payload["start"],
            end=retention_payload["end"],
        )

    if not allow_omit and retention.mode == "omit":
        raise ValueError("최종 보존 재선택에서는 omit을 사용할 수 없습니다.")

    # 실제 저장과 같은 선택 함수를 사용해 범위 오류를 모델 경계에서 막는다.
    selected_content = select_retained_content(
        raw_text,
        retention,
        max_chunk_characters=max_selected_characters,
    )

    if (
        selected_content is not None
        and len(selected_content) > max_selected_characters
    ):
        raise ValueError(
            "선택한 도구 본문은 "
            f"{max_selected_characters}자를 넘을 수 없습니다."
        )

    return retention


def parse_node1_recovery_choice(payload, candidate_count):
    """Node1이 실제 후보 범위 안에서 원문 하나를 고르게 한다."""

    if not _is_plain_positive_integer(candidate_count):
        raise ValueError("candidate_count는 1 이상의 정수여야 합니다.")

    choice_payload = _require_exact_object(
        payload,
        {"candidate_number"},
        "Node1RecoveryChoice",
    )
    choice = Node1RecoveryChoice(
        candidate_number=choice_payload["candidate_number"],
    )

    if choice.candidate_number > candidate_count:
        raise ValueError(
            "candidate_number가 복구 가능한 후보 범위를 벗어났습니다."
        )

    return choice


def parse_node1_recovery_retention(
    payload,
    raw_text,
    max_selected_characters=DEFAULT_MAX_SELECTED_CHARACTERS,
):
    """최종 재선택에서 짧은 원문 방식 또는 긴 원문 chunk만 허용한다."""

    if not _is_plain_positive_integer(max_selected_characters):
        raise ValueError(
            "max_selected_characters는 1 이상의 정수여야 합니다."
        )

    response_payload = _require_exact_object(
        payload,
        {"retention"},
        "Node1RecoveryRetention",
    )
    return _parse_retention(
        response_payload["retention"],
        raw_text,
        max_selected_characters,
        allow_omit=False,
    )


def parse_review_decision(payload):
    """엄격한 JSON 객체를 Node2·Node4의 ``ReviewDecision``으로 검증한다."""

    decision = _require_exact_object(
        payload,
        {"verdict", "reason"},
        "ReviewDecision",
    )
    return ReviewDecision(
        verdict=decision["verdict"],
        reason=decision["reason"],
    )


def parse_node3_answer(payload):
    """엄격한 JSON 객체를 ``Node3Answer``로 검증한다."""

    answer = _require_exact_object(
        payload,
        {"answer"},
        "Node3Answer",
    )
    return Node3Answer(answer=answer["answer"])
