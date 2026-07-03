from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataRecord, DataStore
from songryeon_core.core.schemas import (
    L2_REVISION_PREVIOUS_TOOL_NAMES,
    L2RevisionInputFrame,
    validate_l2_revision_input_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.l_loop_namespace import LRunIds
from songryeon_core.nodes.l1_goal_setter import L1_GOAL_FRAME_DATA_ID
from songryeon_core.nodes.node_0_memory_supplier import (
    L3_CONTINUATION_SUMMARY_MODE,
    memory_packet_data_id,
)


L2_REVISION_INPUT_DATA_TYPE = "node_input:L2_revision_input_frame"
L2_REVISION_INPUT_DATA_ID_PREFIX = "L2:revision_input"


def l2_revision_input_data_id(
    attempt_index: int,
    *,
    id_namespace: LRunIds | None = None,
) -> str:
    """L2 revision input frame의 DataStore ID를 만든다."""

    legacy_id = f"{L2_REVISION_INPUT_DATA_ID_PREFIX}:{attempt_index:04d}"
    if id_namespace is None:
        return legacy_id
    return id_namespace.scoped_data_id(legacy_id)


def record_l2_revision_input_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    continuation_frame_id: str,
    memory_packet_id: str | None = None,
    l1_goal_data_id: str = L1_GOAL_FRAME_DATA_ID,
    id_namespace: LRunIds | None = None,
) -> tuple[str, str, L2RevisionInputFrame]:
    """L2가 재검색 계획을 세울 때 받을 입력 frame을 기록한다.

    이 함수는 L2를 실행하지 않는다. 이미 존재하는 구조화 record를 읽고,
    L2가 다음 단계에서 볼 입력 묶음을 DataStore에 남기는 역할만 한다.

    중요한 경계:
    - L3의 reason 문장을 코드가 해석하지 않는다.
    - 검색 후보 제목이나 preview의 의미를 코드가 판단하지 않는다.
    - 예산과 상태 같은 구조화 필드만 계산하고, 자유 텍스트는 복사한다.

    l1_goal_data_id를 인자로 받는 이유:
    재검색 입력도 원래 L1 목표를 다시 읽는다. L루프 2회차 이상에서는
    `L1:goal_frame`이 아니라 run-scoped L1 목표를 읽어야 목표가 섞이지 않는다.
    """

    continuation_payload = _require_payload(data_store, continuation_frame_id)
    attempt_index = _required_int(continuation_payload, "attempt_index")
    if _required_text(continuation_payload, "continuation_status") != "continue":
        raise ValueError("L2 revision input can be recorded only for continuation_status=continue")

    resolved_memory_packet_id = memory_packet_id or (
        id_namespace.memory_packet_data_id(
            target="L2",
            mode=L3_CONTINUATION_SUMMARY_MODE,
            packet_id_suffix=f"{attempt_index:04d}",
        )
        if id_namespace is not None
        else memory_packet_data_id(
            "L2",
            L3_CONTINUATION_SUMMARY_MODE,
            f"{attempt_index:04d}",
        )
    )
    source_l3_id = _required_text(continuation_payload, "source_l3_achievement_id")
    source_l2_id = _required_text(continuation_payload, "source_l2_query_frame_id")
    l1_record = data_store.require_record(l1_goal_data_id)
    l2_record = data_store.require_record(source_l2_id)
    l3_record = data_store.require_record(source_l3_id)
    continuation_record = data_store.require_record(continuation_frame_id)
    memory_record = data_store.require_record(resolved_memory_packet_id)

    l1_payload = _require_dict_payload(l1_record)
    l2_payload = _require_dict_payload(l2_record)
    l3_payload = _require_dict_payload(l3_record)
    memory_payload = _require_dict_payload(memory_record)
    latest_budget_record = _latest_budget_record(
        data_store,
        turn_id,
        id_namespace=id_namespace,
    )
    latest_budget_payload = (
        _require_dict_payload(latest_budget_record) if latest_budget_record is not None else {}
    )

    frame_id = l2_revision_input_data_id(
        attempt_index,
        id_namespace=id_namespace,
    )
    source_data_ids = _unique_strings(
        [
            continuation_frame_id,
            l1_goal_data_id,
            source_l2_id,
            source_l3_id,
            resolved_memory_packet_id,
            latest_budget_record.data_id if latest_budget_record is not None else None,
        ]
    )
    source_trace_ids = _unique_strings(
        [
            continuation_record.source_trace_id,
            l1_record.source_trace_id,
            l2_record.source_trace_id,
            l3_record.source_trace_id,
            memory_record.source_trace_id,
            latest_budget_record.source_trace_id if latest_budget_record is not None else None,
            *_string_list(continuation_payload.get("source_trace_ids")),
            *_string_list(memory_payload.get("source_trace_ids")),
        ]
    )

    # 읽은 문서와 아직 읽지 않은 후보는 continuation frame의 구조화 필드만 복사한다.
    # 후보 preview가 있으면 tool distillation에서 doc_id가 정확히 일치하는 것만 붙인다.
    read_doc_ids = _string_list(continuation_payload.get("read_doc_ids"))
    unread_candidate_doc_ids = _string_list(continuation_payload.get("unread_candidate_doc_ids"))
    preview_by_doc_id = _search_preview_by_doc_id(data_store)
    unread_candidate_summaries = [
        _candidate_summary(doc_id=doc_id, preview=preview_by_doc_id.get(doc_id))
        for doc_id in unread_candidate_doc_ids
    ]

    frame = L2RevisionInputFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        attempt_index=attempt_index,
        max_attempts=_required_int(continuation_payload, "max_attempts"),
        macro_goal=_required_text(l1_payload, "macro_goal"),
        micro_goal=_required_text(l1_payload, "micro_goal"),
        previous_query_text=_text(l2_payload, "query_text", fallback="unknown_query"),
        previous_tool_name=_previous_tool_name(data_store=data_store, l2_payload=l2_payload),
        read_document_names=read_doc_ids,
        unread_candidate_doc_ids=unread_candidate_doc_ids,
        unread_candidate_summaries=unread_candidate_summaries,
        l3_goal_status=_text(l3_payload, "achievement_status", fallback="not_run"),
        l3_goal_match_status=_text(l3_payload, "goal_match_status", fallback="not_run"),
        l3_semantic_goal_match_status=_text(
            l3_payload,
            "semantic_goal_match_status",
            fallback="not_run",
        ),
        l3_feedback_text=_l3_feedback_text(l3_payload),
        remaining_tool_calls=_remaining_budget(
            latest_budget_payload,
            max_field="max_tool_calls",
            used_field="tool_call_count",
        ),
        remaining_query_attempts=_remaining_budget(
            latest_budget_payload,
            max_field="max_query_attempts",
            used_field="query_count",
        ),
        remaining_read_doc_calls=_remaining_budget(
            latest_budget_payload,
            max_field="max_read_doc_calls",
            used_field="read_doc_count",
        ),
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
    )
    validate_l2_revision_input_frame(frame)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="L2",
        event_type="node_input",
        input_ref=source_trace_ids,
        output_ref=[frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame_id,
        data_type=L2_REVISION_INPUT_DATA_TYPE,
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, frame_id, frame


def _require_payload(data_store: DataStore, data_id: str) -> dict[str, object]:
    record = data_store.require_record(data_id)
    return _require_dict_payload(record)


def _require_dict_payload(record: DataRecord) -> dict[str, object]:
    if not isinstance(record.payload, dict):
        raise TypeError(f"{record.data_id} payload must be a dict")
    return record.payload


def _required_text(payload: dict[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if isinstance(value, str) and value.strip():
        return value
    raise ValueError(f"{field_name} must be a non-empty string")


def _required_int(payload: dict[str, object], field_name: str) -> int:
    value = payload.get(field_name)
    if isinstance(value, int):
        return value
    raise ValueError(f"{field_name} must be an integer")


def _text(payload: dict[str, object], field_name: str, *, fallback: str) -> str:
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


def _latest_budget_record(
    data_store: DataStore,
    turn_id: str,
    *,
    id_namespace: LRunIds | None,
) -> DataRecord | None:
    latest_record: DataRecord | None = None
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


def _remaining_budget(payload: dict[str, object], *, max_field: str, used_field: str) -> int:
    max_value = payload.get(max_field)
    used_value = payload.get(used_field)
    if not isinstance(max_value, int) or not isinstance(used_value, int):
        return 0
    return max(max_value - used_value, 0)


def _previous_tool_name(*, data_store: DataStore, l2_payload: dict[str, object]) -> str:
    """마지막으로 실제 실행된 L 관련 도구 이름을 구조화 record에서 찾는다."""

    latest_tool_name: str | None = None
    for record in data_store.list_records():
        if not record.data_type.startswith("tool_result:"):
            continue
        tool_name = record.data_type.split(":", 1)[1]
        if tool_name in L2_REVISION_PREVIOUS_TOOL_NAMES:
            latest_tool_name = tool_name
    if latest_tool_name is not None:
        return latest_tool_name

    target_tool_name = _text(l2_payload, "target_tool_name", fallback="search_docs")
    if target_tool_name in L2_REVISION_PREVIOUS_TOOL_NAMES:
        return target_tool_name
    return "search_docs"


def _search_preview_by_doc_id(data_store: DataStore) -> dict[str, str]:
    previews: dict[str, str] = {}
    for record in data_store.list_records():
        if not record.data_type.startswith("tool_result_distillation:"):
            continue
        if not isinstance(record.payload, dict):
            continue
        items = record.payload.get("items")
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("item_kind") != "search_result":
                continue
            doc_id = item.get("doc_id")
            preview = item.get("text_preview")
            if isinstance(doc_id, str) and doc_id and isinstance(preview, str) and preview:
                previews.setdefault(doc_id, preview)
    return previews


def _candidate_summary(*, doc_id: str, preview: str | None) -> str:
    if preview:
        return f"doc_id={doc_id}; preview={preview}"
    return f"doc_id={doc_id}"


def _l3_feedback_text(l3_payload: dict[str, object]) -> str:
    # L3가 쓴 이유 문장은 그대로 복사한다. 여기서 의미를 해석하지 않는다.
    return " | ".join(
        value
        for value in [
            _text(l3_payload, "reason", fallback=""),
            _text(l3_payload, "macro_achievement_reason", fallback=""),
            _text(l3_payload, "micro_achievement_reason", fallback=""),
            _text(l3_payload, "semantic_goal_match_reason", fallback=""),
        ]
        if value
    )


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
