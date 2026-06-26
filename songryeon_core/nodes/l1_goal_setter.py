from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    L1GoalFrame,
    MemoryPacketFrom0,
    TraceEvent,
    validate_l1_goal_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutor


L1_GOAL_FRAME_DATA_ID = "L1:goal_frame"


def run_l1_goal_setter(
    *,
    trace_store: TraceStore,
    data_store: DataStore | None = None,
    turn_id: str,
    memory_packet: MemoryPacketFrom0,
    user_query: str = "",
    source_data_ids: list[str] | None = None,
    adapter: LLMAdapter | None = None,
    goal_frame_data_id: str = L1_GOAL_FRAME_DATA_ID,
) -> TraceEvent:
    """L1 목표 설정 노드의 규칙 기반 드라이런 실행.

    goal_frame_data_id를 인자로 받는 이유:
    첫 L루프는 `L1:goal_frame`을 유지하지만, 같은 턴에서 L을 다시 돌릴 때는
    `L:run:0002:L1:goal_frame`처럼 실행 회차별 ID를 써야 DataStore 충돌이 나지 않는다.
    """

    if adapter is not None and data_store is not None:
        try:
            frame = _run_l1_goal_llm(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                memory_packet=memory_packet,
                user_query=user_query,
                source_data_ids=source_data_ids or [],
                adapter=adapter,
                goal_frame_data_id=goal_frame_data_id,
            )
        except Exception:
            frame = _rule_stub_goal_frame(
                turn_id=turn_id,
                memory_packet=memory_packet,
                source_data_ids=source_data_ids or [],
                goal_frame_data_id=goal_frame_data_id,
            )
    else:
        frame = _rule_stub_goal_frame(
            turn_id=turn_id,
            memory_packet=memory_packet,
            source_data_ids=source_data_ids or [],
            goal_frame_data_id=goal_frame_data_id,
        )
    validate_l1_goal_frame(frame)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="L1",
        event_type="node_output",
        input_ref=memory_packet.trace_evidence_ids,
        output_ref=[goal_frame_data_id],
        schema_status="passed",
    )
    if data_store is not None:
        data_store.create_record(
            data_id=goal_frame_data_id,
            data_type="node_output:L1_goal_frame",
            exists=True,
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            payload=asdict(frame),
        )
    return event


def _rule_stub_goal_frame(
    *,
    turn_id: str,
    memory_packet: MemoryPacketFrom0,
    source_data_ids: list[str],
    goal_frame_data_id: str,
) -> L1GoalFrame:
    # RULE_STUB 경로도 LLM 경로와 같은 frame_id를 써야 한다.
    # 그래야 LLM 실패 fallback이 실행돼도 run-scoped ID 계약이 깨지지 않는다.
    return L1GoalFrame(
        frame_id=goal_frame_data_id,
        turn_id=turn_id,
        macro_goal="produce_l_loop_evidence_material_for_current_request",
        macro_goal_reason="CODE_STATUS:l_route_final_evidence_material_stub",
        micro_goal="prepare_first_document_lookup_action",
        micro_goal_reason="CODE_STATUS:first_search_or_read_preparation_stub",
        goal_source="rule_based_l_route",
        target_loop="L",
        evidence_requirement_kind="unspecified",
        minimum_read_documents=0,
        requires_cross_document_analysis=False,
        randomness_mode="not_random",
        l_loop_success_condition="CODE_STATUS:rule_stub_requires_evidence_material_or_insufficiency_signal",
        goal_generation_source="RULE_STUB",
        llm_goal_judgement_status="not_run",
        source_trace_ids=memory_packet.trace_evidence_ids,
        source_data_ids=source_data_ids,
    )


def _run_l1_goal_llm(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    memory_packet: MemoryPacketFrom0,
    user_query: str,
    source_data_ids: list[str],
    adapter: LLMAdapter,
    goal_frame_data_id: str,
) -> L1GoalFrame:
    prompt_ref = "songryeon_core/prompts/l1_goal_setter_v0.md"
    prompt = Path(prompt_ref).read_text(encoding="utf-8")
    input_payload = {
        "target_loop": "L",
        "user_query": user_query,
        "memory_packet": {
            "target": memory_packet.target,
            "trace_evidence_ids": memory_packet.trace_evidence_ids,
            "insufficient_signal_id": memory_packet.insufficient_signal_id,
        },
        "source_data_ids": source_data_ids,
        "required_output_fields": [
            "macro_goal",
            "macro_goal_reason",
            "micro_goal",
            "micro_goal_reason",
            "evidence_requirement_kind",
            "minimum_read_documents",
            "requires_cross_document_analysis",
            "randomness_mode",
            "l_loop_success_condition",
            "requested_search_top_k",
            "requested_max_tool_calls",
            "requested_max_read_doc_calls",
            "requested_max_query_attempts",
            "budget_request_reason",
        ],
    }
    llm_result = LLMNodeExecutor(adapter).run(
        node_id="L1",
        prompt=prompt,
        input_payload=input_payload,
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=prompt_ref,
        input_ref=memory_packet.trace_evidence_ids,
        source_data_ids=source_data_ids,
        payload_validator=_validate_l1_goal_payload,
    )
    if llm_result.failure_type != "none" or llm_result.validation.payload is None:
        raise ValueError(f"L1 LLM goal setter failed: {llm_result.failure_type}")

    frame_source_trace_ids = list(memory_packet.trace_evidence_ids)
    if llm_result.trace_event_id:
        frame_source_trace_ids.append(llm_result.trace_event_id)
    frame_source_data_ids = list(source_data_ids)
    if llm_result.call_data_id:
        frame_source_data_ids.append(llm_result.call_data_id)

    payload = llm_result.validation.payload
    return L1GoalFrame(
        frame_id=goal_frame_data_id,
        turn_id=turn_id,
        macro_goal=str(payload.get("macro_goal") or "").strip(),
        macro_goal_reason=str(payload.get("macro_goal_reason") or "").strip(),
        micro_goal=str(payload.get("micro_goal") or "").strip(),
        micro_goal_reason=str(payload.get("micro_goal_reason") or "").strip(),
        goal_source="llm_l_route",
        target_loop="L",
        evidence_requirement_kind=str(payload.get("evidence_requirement_kind") or "").strip(),
        minimum_read_documents=_nonnegative_int(payload.get("minimum_read_documents")),
        requires_cross_document_analysis=_bool_value(
            payload.get("requires_cross_document_analysis")
        ),
        randomness_mode=str(payload.get("randomness_mode") or "").strip(),
        l_loop_success_condition=str(payload.get("l_loop_success_condition") or "").strip(),
        requested_search_top_k=_nonnegative_int(payload.get("requested_search_top_k")),
        requested_max_tool_calls=_nonnegative_int(payload.get("requested_max_tool_calls")),
        requested_max_read_doc_calls=_nonnegative_int(payload.get("requested_max_read_doc_calls")),
        requested_max_query_attempts=_nonnegative_int(payload.get("requested_max_query_attempts")),
        budget_request_reason=str(payload.get("budget_request_reason") or "").strip(),
        goal_generation_source=f"LLM:{llm_result.model_id}",
        llm_goal_judgement_status="ran",
        source_trace_ids=_unique_strings(frame_source_trace_ids),
        source_data_ids=_unique_strings(frame_source_data_ids),
    )


def _validate_l1_goal_payload(payload: dict[str, object]) -> None:
    frame = L1GoalFrame(
        frame_id=L1_GOAL_FRAME_DATA_ID,
        turn_id="validation_turn",
        macro_goal=str(payload.get("macro_goal") or "").strip(),
        macro_goal_reason=str(payload.get("macro_goal_reason") or "").strip(),
        micro_goal=str(payload.get("micro_goal") or "").strip(),
        micro_goal_reason=str(payload.get("micro_goal_reason") or "").strip(),
        goal_source="llm_l_route",
        target_loop="L",
        evidence_requirement_kind=str(payload.get("evidence_requirement_kind") or "").strip(),
        minimum_read_documents=_nonnegative_int(payload.get("minimum_read_documents")),
        requires_cross_document_analysis=_bool_value(
            payload.get("requires_cross_document_analysis")
        ),
        randomness_mode=str(payload.get("randomness_mode") or "").strip(),
        l_loop_success_condition=str(payload.get("l_loop_success_condition") or "").strip(),
        requested_search_top_k=_nonnegative_int(payload.get("requested_search_top_k")),
        requested_max_tool_calls=_nonnegative_int(payload.get("requested_max_tool_calls")),
        requested_max_read_doc_calls=_nonnegative_int(payload.get("requested_max_read_doc_calls")),
        requested_max_query_attempts=_nonnegative_int(payload.get("requested_max_query_attempts")),
        budget_request_reason=str(payload.get("budget_request_reason") or "").strip(),
        goal_generation_source="LLM:validation-model",
        llm_goal_judgement_status="ran",
        source_trace_ids=["validation_trace"],
        source_data_ids=["validation_data"],
    )
    validate_l1_goal_frame(frame)


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


def _nonnegative_int(value: object) -> int:
    if value is None or value == "":
        return 0
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, number)


def _bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
    return False
