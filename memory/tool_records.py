"""실제 도구 원문과 Node1의 본문 보존 결정을 기록한다."""

from nodes import (
    RetentionDecision,
    resolve_text_chunk,
    select_retained_content,
)

from .audit import (
    canonical_json,
    new_audit_record,
    validate_visible_batch,
)
from .settings import (
    DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    DEFAULT_MEMORY_PATH,
)
from .store import append_information_records
from .tool_source import (
    verify_omitted_tool_source,
    verify_saved_tool_source,
)


def _selection_payloads(decision, raw_text):
    """Node1의 R 요청과 코드가 확인한 적용 범위를 분리한다."""

    if decision.mode == "chunk":
        chunk = resolve_text_chunk(raw_text, decision.chunk_id)
        requested = {
            "chunk_id": decision.chunk_id,
            "mode": "chunk",
        }
        applied = {
            **requested,
            "end": chunk.end,
            "start": chunk.start,
        }
        return requested, applied

    requested = {
        "end": decision.end,
        "mode": decision.mode,
        "start": decision.start,
    }
    return requested, dict(requested)


def save_tool_observation(
    *,
    tool_name,
    arguments,
    success,
    content,
    error,
    source_node,
    round_number,
    attempt_number,
    maximum_attempts,
    turn_id,
    memory_path=DEFAULT_MEMORY_PATH,
):
    """실제 도구 행동과 숨김 원문을 한 번의 append로 먼저 저장한다."""

    action = canonical_json(
        {
            "arguments": arguments,
            "tool_name": tool_name,
        }
    )
    use_count = canonical_json(
        {
            "attempt": attempt_number,
            "maximum": maximum_attempts,
            "round": round_number,
        }
    )
    records = [
        new_audit_record(source_node, "absolute", "source", turn_id),
        new_audit_record(action, "absolute", "action", turn_id),
        new_audit_record(
            "success" if success else "error",
            "absolute",
            "tool_status",
            turn_id,
        ),
        new_audit_record(
            use_count,
            "absolute",
            "tool_use_count",
            turn_id,
        ),
        new_audit_record(
            tool_name,
            "absolute",
            "tool_raw_name",
            turn_id,
        ),
        new_audit_record(
            canonical_json(arguments),
            "absolute",
            "tool_raw_arguments",
            turn_id,
        ),
        new_audit_record(
            success,
            "absolute",
            "tool_raw_success",
            turn_id,
        ),
        new_audit_record(
            content,
            "absolute",
            "tool_raw_content",
            turn_id,
        ),
        new_audit_record(
            error or "",
            "absolute",
            "tool_raw_error",
            turn_id,
        ),
    ]

    validate_visible_batch(
        records,
        DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    )
    return append_information_records(records, memory_path)


def save_node1_retention(
    *,
    decision,
    source_information_id,
    turn_id,
    memory_path=DEFAULT_MEMORY_PATH,
    max_characters=DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
):
    """저장된 원문을 다시 검증해 Node1의 R 판단과 A 선택을 저장한다."""

    if not isinstance(decision, RetentionDecision):
        raise TypeError("decision은 RetentionDecision이어야 합니다.")

    tool_name, arguments, raw_text = verify_saved_tool_source(
        memory_path,
        source_information_id,
        turn_id,
    )
    selected_content = select_retained_content(raw_text, decision)

    requested_selection, applied_selection = _selection_payloads(
        decision,
        raw_text,
    )
    applied_selection = {
        **applied_selection,
        "arguments": arguments,
        "tool_name": tool_name,
    }
    records = [
        # 추적용 원본 ID는 에이전트 시야가 아닌 숨김 감사 기록에만 둔다.
        new_audit_record(
            source_information_id,
            "absolute",
            "tool_raw_selection_source_id",
            turn_id,
        ),
        new_audit_record(
            decision.review,
            "relative",
            "node1_tool_review",
            turn_id,
        ),
        new_audit_record(
            canonical_json(requested_selection),
            "relative",
            "node1_retention_request",
            turn_id,
        ),
        new_audit_record(
            canonical_json(applied_selection),
            "absolute",
            "tool_retention_applied",
            turn_id,
        ),
    ]

    if selected_content is not None:
        records.append(
            new_audit_record(
                selected_content,
                "absolute",
                "tool_result_content",
                turn_id,
            )
        )

    # 검증 실패 시 append를 호출하지 않아 숨김 원문만 남는다.
    validate_visible_batch(records, max_characters)
    saved_records = append_information_records(records, memory_path)
    return selected_content, saved_records


def save_node1_all_omit_detection(
    *,
    round_number,
    candidate_count,
    turn_id,
    memory_path=DEFAULT_MEMORY_PATH,
):
    """코드가 감지한 현재 라운드의 전부 omit 상태를 A로 기록한다."""

    for value, field_name in (
        (round_number, "round_number"),
        (candidate_count, "candidate_count"),
    ):
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
        ):
            raise ValueError(f"{field_name}는 1 이상의 정수여야 합니다.")

    detection = canonical_json(
        {
            "candidate_count": candidate_count,
            "recovery_number": 1,
            "round": round_number,
        }
    )
    records = [
        new_audit_record("runtime", "absolute", "source", turn_id),
        new_audit_record(
            detection,
            "absolute",
            "node1_all_omit_detected",
            turn_id,
        ),
    ]

    validate_visible_batch(
        records,
        DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    )
    return append_information_records(records, memory_path)


def save_node1_omit_recovery(
    *,
    decision,
    candidate_number,
    source_information_id,
    turn_id,
    memory_path=DEFAULT_MEMORY_PATH,
    max_characters=DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
):
    """기존 omit을 보존한 채 선택한 원문 A를 추가한다."""

    if not isinstance(decision, RetentionDecision):
        raise TypeError("decision은 RetentionDecision이어야 합니다.")

    if decision.mode == "omit":
        raise ValueError(
            "omit 복구에는 full, excerpt 또는 chunk가 필요합니다."
        )

    if (
        not isinstance(candidate_number, int)
        or isinstance(candidate_number, bool)
        or candidate_number < 1
    ):
        raise ValueError("candidate_number는 1 이상의 정수여야 합니다.")

    tool_name, arguments, raw_text = verify_omitted_tool_source(
        memory_path,
        source_information_id,
        turn_id,
    )
    selected_content = select_retained_content(raw_text, decision)

    requested_base, applied_base = _selection_payloads(
        decision,
        raw_text,
    )
    requested_selection = {
        "candidate_number": candidate_number,
        **requested_base,
    }
    applied_selection = {
        "candidate_number": candidate_number,
        **applied_base,
        "arguments": arguments,
        "previous_mode": "omit",
        "tool_name": tool_name,
    }
    records = [
        new_audit_record(
            source_information_id,
            "absolute",
            "tool_raw_omit_recovery_source_id",
            turn_id,
        ),
        new_audit_record(
            decision.review,
            "relative",
            "node1_omit_recovery_review",
            turn_id,
        ),
        new_audit_record(
            canonical_json(requested_selection),
            "relative",
            "node1_omit_recovery_request",
            turn_id,
        ),
        new_audit_record(
            canonical_json(applied_selection),
            "absolute",
            "tool_omit_recovery_applied",
            turn_id,
        ),
        new_audit_record(
            selected_content,
            "absolute",
            "tool_result_content",
            turn_id,
        ),
    ]

    validate_visible_batch(records, max_characters)
    saved_records = append_information_records(records, memory_path)
    return selected_content, saved_records
