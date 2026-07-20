from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    L_LOOP_FINAL_STATE_INDEX_DATA_TYPE,
    L_LOOP_PRE_REVISION_CONTROL_SCOPE,
    LLoopFinalStateIndexFrame,
    validate_l_loop_final_state_index_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.l_loop_namespace import LRunIds


L3_ACHIEVEMENT_DATA_TYPES = {
    "node_output:L3_achievement_frame",
    "node_output:L3_revision_achievement_frame",
}
L_LOOP_CONTROL_DATA_TYPE = "node_output:L_loop_control_frame"
L_LOOP_CONTINUATION_DATA_TYPE = "node_output:L_loop_continuation_frame"


def record_l_loop_final_state_index(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    latest_l3_achievement_data_id: str,
    pre_revision_terminal_control_data_id: str | None,
    final_continuation_data_id: str | None,
    id_namespace: LRunIds | None = None,
) -> tuple[str, str, LLoopFinalStateIndexFrame]:
    """최초 control과 revision 포함 최신 상태의 좌표를 한 record로 묶는다.

    이 함수는 성공/실패 의미를 새로 판단하지 않는다. 이미 존재하는 L3와
    continuation payload의 구조화 필드를 복사하고 canonical source ID만 고른다.
    """

    latest_l3_record = data_store.require_record(latest_l3_achievement_data_id)
    if latest_l3_record.data_type not in L3_ACHIEVEMENT_DATA_TYPES:
        raise ValueError("latest L3 source must be an achievement frame")
    latest_l3_payload = _payload(latest_l3_record.payload, owner="latest L3 achievement")
    latest_l3_status = _required_text(latest_l3_payload, "achievement_status")
    latest_l3_generation_source = _required_text(
        latest_l3_payload,
        "achievement_generation_source",
    )

    pre_revision_decision = "not_recorded"
    pre_revision_trace_id: str | None = None
    if pre_revision_terminal_control_data_id is not None:
        control_record = data_store.require_record(pre_revision_terminal_control_data_id)
        if control_record.data_type != L_LOOP_CONTROL_DATA_TYPE:
            raise ValueError("pre-revision control source must be an LLoopControlFrame")
        control_payload = _payload(control_record.payload, owner="pre-revision control")
        pre_revision_decision = _required_text(control_payload, "decision")
        pre_revision_trace_id = control_record.source_trace_id

    final_continuation_status = "not_recorded"
    final_continuation_trace_id: str | None = None
    if final_continuation_data_id is not None:
        continuation_record = data_store.require_record(final_continuation_data_id)
        if continuation_record.data_type != L_LOOP_CONTINUATION_DATA_TYPE:
            raise ValueError("final continuation source must be an LLoopContinuationFrame")
        continuation_payload = _payload(
            continuation_record.payload,
            owner="final continuation",
        )
        final_continuation_status = _required_text(
            continuation_payload,
            "continuation_status",
        )
        final_continuation_trace_id = continuation_record.source_trace_id

    frame_id = (
        id_namespace.final_state_index_frame_id()
        if id_namespace is not None
        else "L:final_state_index_frame"
    )
    source_data_ids = _unique_strings(
        [
            pre_revision_terminal_control_data_id,
            latest_l3_achievement_data_id,
            final_continuation_data_id,
        ]
    )
    source_trace_ids = _unique_strings(
        [
            pre_revision_trace_id,
            latest_l3_record.source_trace_id,
            final_continuation_trace_id,
        ]
    )
    frame = LLoopFinalStateIndexFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        run_index=id_namespace.run_index if id_namespace is not None else 1,
        pre_revision_terminal_control_data_id=pre_revision_terminal_control_data_id,
        pre_revision_terminal_control_decision=pre_revision_decision,
        pre_revision_terminal_control_scope=L_LOOP_PRE_REVISION_CONTROL_SCOPE,
        latest_l3_achievement_data_id=latest_l3_achievement_data_id,
        latest_l3_achievement_status=latest_l3_status,
        latest_l3_achievement_generation_source=latest_l3_generation_source,
        final_continuation_data_id=final_continuation_data_id,
        final_continuation_status=final_continuation_status,
        final_status_source_data_id=latest_l3_achievement_data_id,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
    )
    validate_l_loop_final_state_index_frame(frame)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="L_final_state_indexer",
        event_type="node_output",
        input_ref=source_trace_ids,
        output_ref=[frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame_id,
        data_type=L_LOOP_FINAL_STATE_INDEX_DATA_TYPE,
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, frame_id, frame


def _payload(value: object, *, owner: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{owner} payload must be a dict")
    return value


def _required_text(payload: dict[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


__all__ = ["record_l_loop_final_state_index"]
