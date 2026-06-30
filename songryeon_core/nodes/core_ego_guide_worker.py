from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    CoreEgoGuideWorkerHintFrame,
    RLoopGraphGuidePacketFrame,
    validate_core_ego_guide_worker_hint_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutor


CORE_EGO_GUIDE_WORKER_NODE_ID = "core_ego_guide_worker"
CORE_EGO_GUIDE_WORKER_PROMPT_REF = (
    "songryeon_core/prompts/core_ego_guide_worker_v0.md"
)


def core_ego_guide_worker_hint_frame_data_id(guide_packet_id: str) -> str:
    return f"{guide_packet_id}:core_ego_guide_worker_hint"


def core_ego_guide_worker_input_data_id(guide_packet_id: str) -> str:
    return f"{guide_packet_id}:core_ego_guide_worker_input"


def run_core_ego_guide_worker_hint(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    guide_packet: RLoopGraphGuidePacketFrame,
    adapter: LLMAdapter | None,
    max_retries: int = 0,
) -> tuple[str, str, CoreEgoGuideWorkerHintFrame]:
    """Ask an LLM for graph traversal hints without changing the code guide packet."""

    frame_id = core_ego_guide_worker_hint_frame_data_id(guide_packet.packet_id)
    input_data_id = core_ego_guide_worker_input_data_id(guide_packet.packet_id)
    base_source_data_ids = _unique_strings(
        [
            guide_packet.packet_id,
            guide_packet.graph_snapshot_id,
            *guide_packet.source_data_ids,
        ]
    )
    input_payload = _guide_worker_input_payload(
        guide_packet=guide_packet,
        input_data_id=input_data_id,
        source_data_ids=base_source_data_ids,
    )
    input_trace_id = _record_guide_worker_input(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        input_data_id=input_data_id,
        input_payload=input_payload,
        source_trace_ids=guide_packet.source_trace_ids,
        source_data_ids=base_source_data_ids,
    )
    base_source_trace_ids = _unique_strings(
        [*guide_packet.source_trace_ids, input_trace_id]
    )

    if adapter is None:
        frame = _failed_hint_frame(
            frame_id=frame_id,
            guide_packet=guide_packet,
            model_id="adapter_missing",
            failure_type="adapter_missing",
            payload_parse_status="not_checked",
            source_trace_ids=base_source_trace_ids,
            source_data_ids=_unique_strings([*base_source_data_ids, input_data_id]),
            llm_call_data_id=None,
            llm_trace_event_id=None,
        )
        return _record_hint_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame=frame,
        )

    prompt = Path(CORE_EGO_GUIDE_WORKER_PROMPT_REF).read_text(encoding="utf-8")
    llm_result = LLMNodeExecutor(adapter).run(
        node_id=CORE_EGO_GUIDE_WORKER_NODE_ID,
        prompt=prompt,
        input_payload=input_payload,
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=CORE_EGO_GUIDE_WORKER_PROMPT_REF,
        input_ref=base_source_trace_ids,
        source_data_ids=_unique_strings([*base_source_data_ids, input_data_id]),
        max_retries=max_retries,
        payload_validator=lambda payload: _validate_guide_worker_payload(
            payload=payload,
            available_entry_node_ids=guide_packet.available_entry_nodes,
            available_source_graph_node_ids=guide_packet.source_graph_node_ids,
            available_source_data_ids=base_source_data_ids,
        ),
    )
    source_trace_ids = _unique_strings(
        [*base_source_trace_ids, llm_result.trace_event_id]
    )
    source_data_ids = _unique_strings(
        [*base_source_data_ids, input_data_id, llm_result.call_data_id]
    )
    if llm_result.failure_type != "none" or llm_result.validation.payload is None:
        frame = _failed_hint_frame(
            frame_id=frame_id,
            guide_packet=guide_packet,
            model_id=llm_result.model_id,
            failure_type=llm_result.failure_type,
            payload_parse_status=_payload_parse_status(llm_result.failure_type),
            source_trace_ids=source_trace_ids,
            source_data_ids=source_data_ids,
            llm_call_data_id=llm_result.call_data_id,
            llm_trace_event_id=llm_result.trace_event_id,
        )
    else:
        frame = _hint_frame_from_payload(
            payload=llm_result.validation.payload,
            frame_id=frame_id,
            guide_packet=guide_packet,
            model_id=llm_result.model_id,
            source_trace_ids=source_trace_ids,
            source_data_ids=source_data_ids,
            llm_call_data_id=llm_result.call_data_id,
            llm_trace_event_id=llm_result.trace_event_id,
        )

    return _record_hint_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        frame=frame,
    )


def _guide_worker_input_payload(
    *,
    guide_packet: RLoopGraphGuidePacketFrame,
    input_data_id: str,
    source_data_ids: list[str],
) -> dict[str, object]:
    return {
        "input_data_id": input_data_id,
        "source_rloop_graph_guide_packet_id": guide_packet.packet_id,
        "graph_snapshot_id": guide_packet.graph_snapshot_id,
        "available_entry_node_ids": list(guide_packet.available_entry_nodes),
        "available_source_graph_node_ids": list(guide_packet.source_graph_node_ids),
        "node_kind_counts": dict(guide_packet.node_kind_counts),
        "data_kind_counts": dict(guide_packet.data_kind_counts),
        "summary_depth_range": list(guide_packet.summary_depth_range),
        "source_leaf_count_range": list(guide_packet.source_leaf_count_range),
        "risky_or_unreviewed_node_ids": list(guide_packet.risky_or_unreviewed_node_ids),
        "source_trace_ids": list(guide_packet.source_trace_ids),
        "source_data_ids": source_data_ids,
        "generated_by": "CODE:CORE_EGO_GUIDE_WORKER_INPUT_BUILDER",
        "semantic_judgement_status": "not_run",
    }


def _record_guide_worker_input(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    input_data_id: str,
    input_payload: dict[str, object],
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> str:
    event = trace_store.create_event(
        turn_id=turn_id,
        actor=CORE_EGO_GUIDE_WORKER_NODE_ID,
        event_type="node_input",
        input_ref=source_trace_ids,
        output_ref=[input_data_id],
        schema_status="not_checked",
    )
    data_store.create_record(
        data_id=input_data_id,
        data_type="node_input:core_ego_guide_worker_input",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload={
            **input_payload,
            "source_trace_ids": source_trace_ids,
            "source_data_ids": source_data_ids,
        },
    )
    return event.event_id


def _record_hint_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    frame: CoreEgoGuideWorkerHintFrame,
) -> tuple[str, str, CoreEgoGuideWorkerHintFrame]:
    validate_core_ego_guide_worker_hint_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor=CORE_EGO_GUIDE_WORKER_NODE_ID,
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[frame.frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame.frame_id,
        data_type="node_output:core_ego_guide_worker_hint_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, frame.frame_id, frame


def _hint_frame_from_payload(
    *,
    payload: dict[str, object],
    frame_id: str,
    guide_packet: RLoopGraphGuidePacketFrame,
    model_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    llm_call_data_id: str | None,
    llm_trace_event_id: str | None,
) -> CoreEgoGuideWorkerHintFrame:
    payload_source_data_ids = _string_list(payload.get("source_data_ids"))
    frame = CoreEgoGuideWorkerHintFrame(
        frame_id=frame_id,
        source_rloop_graph_guide_packet_id=guide_packet.packet_id,
        graph_snapshot_id=guide_packet.graph_snapshot_id,
        available_entry_node_ids=list(guide_packet.available_entry_nodes),
        available_source_graph_node_ids=list(guide_packet.source_graph_node_ids),
        recommended_entry_node_ids=_string_list(payload.get("recommended_entry_node_ids")),
        avoid_entry_node_ids=_string_list(payload.get("avoid_entry_node_ids")),
        traversal_strategy_hint=str(payload.get("traversal_strategy_hint") or "").strip(),
        reason_summary=str(payload.get("reason_summary") or "").strip(),
        risk_notes=_string_list(payload.get("risk_notes")),
        expected_depth_policy=str(payload.get("expected_depth_policy") or "").strip(),
        hint_status="ran",
        failure_type="none",
        payload_parse_status="passed",
        llm_call_data_id=llm_call_data_id,
        llm_trace_event_id=llm_trace_event_id,
        prompt_ref=CORE_EGO_GUIDE_WORKER_PROMPT_REF,
        source_graph_node_ids=_string_list(payload.get("source_graph_node_ids")),
        source_trace_ids=source_trace_ids,
        source_data_ids=_unique_strings([*source_data_ids, *payload_source_data_ids]),
        generated_by=f"LLM:{model_id}:core_ego_guide_worker",
        info_class="mixed",
        source_mode="source_bundle",
        claim_alignment="multi_source_bundle",
        semantic_judgement_status="ran",
    )
    validate_core_ego_guide_worker_hint_frame(frame)
    return frame


def _failed_hint_frame(
    *,
    frame_id: str,
    guide_packet: RLoopGraphGuidePacketFrame,
    model_id: str,
    failure_type: str,
    payload_parse_status: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    llm_call_data_id: str | None,
    llm_trace_event_id: str | None,
) -> CoreEgoGuideWorkerHintFrame:
    frame = CoreEgoGuideWorkerHintFrame(
        frame_id=frame_id,
        source_rloop_graph_guide_packet_id=guide_packet.packet_id,
        graph_snapshot_id=guide_packet.graph_snapshot_id,
        available_entry_node_ids=list(guide_packet.available_entry_nodes),
        available_source_graph_node_ids=list(guide_packet.source_graph_node_ids),
        recommended_entry_node_ids=[],
        avoid_entry_node_ids=[],
        traversal_strategy_hint="",
        reason_summary="",
        risk_notes=[],
        expected_depth_policy="",
        hint_status="failed",
        failure_type=failure_type,
        payload_parse_status=payload_parse_status,
        llm_call_data_id=llm_call_data_id,
        llm_trace_event_id=llm_trace_event_id,
        prompt_ref=CORE_EGO_GUIDE_WORKER_PROMPT_REF,
        source_graph_node_ids=[],
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
        generated_by=f"LLM:{model_id}:core_ego_guide_worker",
        info_class="mixed",
        source_mode="source_bundle",
        claim_alignment="multi_source_bundle",
        semantic_judgement_status="failed",
    )
    validate_core_ego_guide_worker_hint_frame(frame)
    return frame


def _validate_guide_worker_payload(
    *,
    payload: dict[str, object],
    available_entry_node_ids: list[str],
    available_source_graph_node_ids: list[str],
    available_source_data_ids: list[str],
) -> None:
    recommended = _string_list(payload.get("recommended_entry_node_ids"))
    avoided = _string_list(payload.get("avoid_entry_node_ids"))
    source_graph_node_ids = _string_list(payload.get("source_graph_node_ids"))
    payload_source_data_ids = _string_list(payload.get("source_data_ids"))

    if len(recommended) != len(set(recommended)):
        raise ValueError("recommended_entry_node_ids must not contain duplicates")
    if len(avoided) != len(set(avoided)):
        raise ValueError("avoid_entry_node_ids must not contain duplicates")
    if len(source_graph_node_ids) != len(set(source_graph_node_ids)):
        raise ValueError("source_graph_node_ids must not contain duplicates")

    available_entries = set(available_entry_node_ids)
    for node_id in [*recommended, *avoided]:
        if node_id not in available_entries:
            raise ValueError("recommended or avoided entry node id is not available")

    available_source_nodes = set(available_source_graph_node_ids)
    for node_id in source_graph_node_ids:
        if node_id not in available_source_nodes:
            raise ValueError("source graph node id is not in graph snapshot")

    available_source_ids = set(available_source_data_ids)
    for data_id in payload_source_data_ids:
        if data_id not in available_source_ids:
            raise ValueError("source_data_id is not in allowed graph guide source bundle")

    traversal_strategy_hint = str(payload.get("traversal_strategy_hint") or "").strip()
    reason_summary = str(payload.get("reason_summary") or "").strip()
    expected_depth_policy = str(payload.get("expected_depth_policy") or "").strip()
    if not traversal_strategy_hint:
        raise ValueError("traversal_strategy_hint must not be empty")
    if not reason_summary:
        raise ValueError("reason_summary must not be empty")
    if not expected_depth_policy:
        raise ValueError("expected_depth_policy must not be empty")
    if not source_graph_node_ids:
        raise ValueError("source_graph_node_ids must not be empty")

    info_class = payload.get("info_class")
    if info_class is not None and info_class != "mixed":
        raise ValueError("CoreEgo guide worker info_class must be mixed when supplied")
    semantic_status = payload.get("semantic_judgement_status")
    if semantic_status is not None and semantic_status != "ran":
        raise ValueError("CoreEgo guide worker semantic_judgement_status must be ran when supplied")


def _payload_parse_status(failure_type: str) -> str:
    if failure_type == "parse_failed":
        return "failed"
    if failure_type == "adapter_failed":
        return "not_checked"
    return "passed"


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item:
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
