from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import LLoopContinuationFrame, validate_l_loop_continuation_frame
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.l_loop_namespace import LRunIds
from songryeon_core.nodes.l2_query_setter import L2_QUERY_FRAME_DATA_ID
from songryeon_core.nodes.l3_result_keeper import L3_ACHIEVEMENT_FRAME_DATA_ID


L_LOOP_CONTINUATION_DATA_TYPE = "node_output:L_loop_continuation_frame"


def record_l_loop_continuation_decision(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    attempt_index: int,
    max_attempts: int = 3,
    source_trace_ids: list[str] | None = None,
    source_data_ids: list[str] | None = None,
    l3_achievement_data_id: str = L3_ACHIEVEMENT_FRAME_DATA_ID,
    l2_query_frame_data_id: str = L2_QUERY_FRAME_DATA_ID,
    id_namespace: LRunIds | None = None,
) -> tuple[str, str, LLoopContinuationFrame]:
    """L3 이후 L루프를 계속할지 멈출지 controller 판단을 기록한다.

    이 함수는 아직 L2를 다시 실행하지 않는다. 지금 단계의 책임은
    "계속할 수 있는 조건인가?"를 구조화된 frame으로 남기는 것이다.

    중요한 경계:
    - L3의 자연어 reason을 해석하지 않는다.
    - L3AchievementFrame의 구조화 status와 tool budget 숫자만 본다.
    - continue가 나오더라도 실제 그래프 재배선은 다음 단계에서 따로 연결한다.
    """

    l3_payload = _require_payload(data_store, l3_achievement_data_id)
    l2_payload = _require_payload(data_store, l2_query_frame_data_id)
    budget_record = _latest_budget_record(data_store, turn_id, id_namespace=id_namespace)
    budget_payload = budget_record.payload if budget_record is not None else {}

    previous_query_text = _text(l2_payload, "query_text", fallback="unknown_query")
    read_doc_ids = _string_list(l3_payload.get("read_doc_ids"))
    search_result_doc_ids = _string_list(l3_payload.get("search_result_doc_ids"))
    unread_candidate_doc_ids = [
        doc_id for doc_id in search_result_doc_ids if doc_id not in set(read_doc_ids)
    ]

    remaining_tool_calls = _remaining_budget(
        budget_payload,
        max_field="max_tool_calls",
        used_field="tool_call_count",
    )
    remaining_query_attempts = _remaining_budget(
        budget_payload,
        max_field="max_query_attempts",
        used_field="query_count",
    )
    remaining_read_doc_calls = _remaining_budget(
        budget_payload,
        max_field="max_read_doc_calls",
        used_field="read_doc_count",
    )
    tool_budget_status = _text(budget_payload, "stop_reason", fallback="within_budget")

    continuation_status, reason_code, next_target_node = _decide_continuation(
        l3_payload=l3_payload,
        attempt_index=attempt_index,
        max_attempts=max_attempts,
        remaining_tool_calls=remaining_tool_calls,
        remaining_query_attempts=remaining_query_attempts,
        remaining_read_doc_calls=remaining_read_doc_calls,
        unread_candidate_doc_ids=unread_candidate_doc_ids,
    )

    frame_id = (
        id_namespace.continuation_data_id(attempt_index)
        if id_namespace is not None
        else f"L:continuation:{attempt_index:04d}"
    )
    frame_source_data_ids = _unique_strings(
        [
            *(source_data_ids or []),
            l3_achievement_data_id,
            l2_query_frame_data_id,
            budget_record.data_id if budget_record is not None else None,
        ]
    )
    frame = LLoopContinuationFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        attempt_index=attempt_index,
        max_attempts=max_attempts,
        continuation_status=continuation_status,
        continuation_reason_code=reason_code,
        source_l3_achievement_id=l3_achievement_data_id,
        source_l2_query_frame_id=l2_query_frame_data_id,
        previous_query_text=previous_query_text,
        read_doc_ids=read_doc_ids,
        unread_candidate_doc_ids=unread_candidate_doc_ids,
        tool_budget_status=tool_budget_status,
        next_target_node=next_target_node,
        source_trace_ids=_unique_strings(source_trace_ids or []),
        source_data_ids=frame_source_data_ids,
    )
    validate_l_loop_continuation_frame(frame)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="L_controller",
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame_id,
        data_type=L_LOOP_CONTINUATION_DATA_TYPE,
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, frame_id, frame


def _decide_continuation(
    *,
    l3_payload: dict[str, object],
    attempt_index: int,
    max_attempts: int,
    remaining_tool_calls: int,
    remaining_query_attempts: int,
    remaining_read_doc_calls: int,
    unread_candidate_doc_ids: list[str],
) -> tuple[str, str, str]:
    """구조화된 status와 예산 숫자만 보고 continuation 상태를 정한다."""

    l3_status = _text(l3_payload, "achievement_status", fallback="failed")
    goal_match_status = _text(l3_payload, "goal_match_status", fallback="not_applicable")
    semantic_match_status = _text(l3_payload, "semantic_goal_match_status", fallback="not_run")
    l3_is_satisfied = (
        l3_status == "achieved"
        and goal_match_status not in {"partial", "missing"}
        and semantic_match_status not in {"partial", "missing"}
    )
    if l3_is_satisfied:
        return "stop_achieved", "CODE_STATUS:l3_achieved", "loop_return_summary"

    if attempt_index >= max_attempts:
        return (
            "stop_failed_final",
            "CODE_STATUS:max_continuation_attempts_reached",
            "loop_return_summary",
        )

    if remaining_tool_calls <= 0:
        return (
            "stop_budget_exhausted",
            "CODE_STATUS:continuation_tool_budget_exhausted",
            "loop_return_summary",
        )

    has_query_budget = remaining_query_attempts > 0
    has_read_budget_for_unread_candidates = remaining_read_doc_calls > 0 and bool(unread_candidate_doc_ids)
    if not has_query_budget and not has_read_budget_for_unread_candidates:
        return (
            "stop_no_actionable_gap",
            "CODE_STATUS:no_unread_candidate_or_revision_plan",
            "loop_return_summary",
        )

    return (
        "continue",
        "CODE_STATUS:l3_not_achieved_and_attempts_remaining",
        "L2",
    )


def _require_payload(data_store: DataStore, data_id: str) -> dict[str, object]:
    record = data_store.require_record(data_id)
    if not isinstance(record.payload, dict):
        raise TypeError(f"{data_id} payload must be a dict")
    return record.payload


def _latest_budget_record(
    data_store: DataStore,
    turn_id: str,
    *,
    id_namespace: LRunIds | None,
):
    latest_record = None
    latest_sequence = -1
    for record in data_store.list_records():
        if record.data_type != "tool_use_budget":
            continue
        if not isinstance(record.payload, dict):
            continue
        if record.payload.get("turn_id") != turn_id:
            continue
        if id_namespace is not None and not id_namespace.owns_data_id(record.data_id):
            continue
        sequence = record.payload.get("sequence_index")
        if isinstance(sequence, int) and sequence > latest_sequence:
            latest_record = record
            latest_sequence = sequence
    return latest_record


def _remaining_budget(payload: object, *, max_field: str, used_field: str) -> int:
    if not isinstance(payload, dict):
        return 0
    max_value = payload.get(max_field)
    used_value = payload.get(used_field)
    if not isinstance(max_value, int) or not isinstance(used_value, int):
        return 0
    return max(max_value - used_value, 0)


def _text(payload: object, field_name: str, *, fallback: str) -> str:
    if not isinstance(payload, dict):
        return fallback
    value = payload.get(field_name)
    if isinstance(value, str) and value.strip():
        return value
    return fallback


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item and item not in result:
            result.append(item)
    return result


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
