from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import record_graph_memory_for_capsules
from songryeon_core.core.graph_memory_export import record_graph_memory_export_packet
from songryeon_core.core.graph_vessel_adapter import record_graph_vessel_write_plan
from songryeon_core.core.schemas import (
    NightTimeBundleSummaryFrame,
    NodeMovement,
    TurnStateCapsule,
    validate_night_time_bundle_summary_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.night_summarize_time_bundle import (
    NIGHT_SUMMARIZE_TIME_BUNDLE_FRAME_DATA_TYPE,
    run_night_summarize_time_bundle,
)


class SummaryPayloadAdapter:
    model_id = "order-166-summary-payload-adapter"

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.last_input_payload: dict[str, object] | None = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.last_input_payload = request.input_payload
        return LLMResponse(
            text=json.dumps(self.payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=self.payload,
        )


def test_time_bundle_summary_for_multiple_capsules_is_mixed_graph_node() -> None:
    trace_store, data_store, time_bundle_id = _store_with_capsules(
        [_sample_capsule("turn_order_166_a"), _sample_capsule("turn_order_166_b")],
        batch_id="batch_order_166_multi",
    )
    adapter = SummaryPayloadAdapter(
        {"summary_text": "This TimeBundle contains two raw capsule coordinate records."}
    )

    result = run_night_summarize_time_bundle(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_166",
        target_time_bundle_node_id=time_bundle_id,
        summary_run_id="001",
        adapter=adapter,
    )

    frame = result.frame
    validate_night_time_bundle_summary_frame(frame)
    assert frame.summary_status == "ran"
    assert frame.info_class == "mixed"
    assert frame.source_mode == "source_bundle"
    assert frame.claim_alignment == "multi_source_bundle"
    assert frame.summary_depth == 1
    assert frame.source_leaf_count == 2
    assert frame.generated_by == f"LLM:{adapter.model_id}:night_summarize_time_bundle"
    assert frame.semantic_judgement_status == "ran"
    assert frame.llm_call_data_id in frame.source_data_ids

    summary_record = data_store.require_record(frame.summary_graph_node_id)
    assert summary_record.data_type == "graph_memory:node:summary"
    assert summary_record.payload["node_kind"] == "summary"
    assert summary_record.payload["target_graph_node_id"] == time_bundle_id

    edge_record = data_store.require_record(result.summary_edge_data_id or "")
    assert edge_record.data_type == "graph_memory:edge:SUMMARY_OF"
    assert edge_record.payload["edge_kind"] == "SUMMARY_OF"
    assert edge_record.payload["from_node_id"] == frame.summary_graph_node_id
    assert edge_record.payload["to_node_id"] == time_bundle_id

    original_time_bundle = data_store.require_record(time_bundle_id)
    assert original_time_bundle.payload["generated_by"] == "CODE:GRAPH_MEMORY_BUILDER"
    assert original_time_bundle.payload["info_class"] == "absolute"
    assert original_time_bundle.payload["semantic_judgement_status"] == "not_run"
    assert "summary_text" not in original_time_bundle.payload

    assert adapter.last_input_payload is not None
    assert adapter.last_input_payload["expected_info_class"] == "mixed"


def test_single_leaf_time_bundle_summary_is_relative() -> None:
    trace_store, data_store, time_bundle_id = _store_with_capsules(
        [_sample_capsule("turn_order_166_single")],
        batch_id="batch_order_166_single",
    )
    adapter = SummaryPayloadAdapter(
        {
            "summary_text": "This TimeBundle contains one raw capsule coordinate record.",
            "info_class": "relative",
        }
    )

    result = run_night_summarize_time_bundle(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_166",
        target_time_bundle_node_id=time_bundle_id,
        summary_run_id="001",
        adapter=adapter,
    )

    frame = result.frame
    assert frame.summary_status == "ran"
    assert frame.info_class == "relative"
    assert frame.source_mode == "single_source"
    assert frame.claim_alignment == "single_absolute_record"
    assert frame.source_leaf_count == 1
    assert len(frame.source_graph_node_ids) == 1


def test_incompatible_llm_info_class_fails_without_graph_summary_node() -> None:
    trace_store, data_store, time_bundle_id = _store_with_capsules(
        [_sample_capsule("turn_order_166_c"), _sample_capsule("turn_order_166_d")],
        batch_id="batch_order_166_bad_class",
    )
    adapter = SummaryPayloadAdapter(
        {
            "summary_text": "This payload intentionally supplies the wrong class.",
            "info_class": "relative",
        }
    )

    result = run_night_summarize_time_bundle(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_166",
        target_time_bundle_node_id=time_bundle_id,
        summary_run_id="001",
        adapter=adapter,
    )

    frame = result.frame
    assert frame.summary_status == "failed"
    assert frame.failure_type == "schema_failed"
    assert frame.summary_text == ""
    assert frame.info_class == "mixed"
    assert frame.semantic_judgement_status == "failed"
    assert result.summary_graph_node_data_id is None
    assert data_store.get_record(frame.summary_graph_node_id) is None
    assert data_store.require_record(frame.frame_id).data_type == (
        NIGHT_SUMMARIZE_TIME_BUNDLE_FRAME_DATA_TYPE
    )
    assert frame.llm_call_data_id is not None
    assert data_store.require_record(frame.llm_call_data_id).payload["failure_type"] == (
        "schema_failed"
    )


def test_summary_node_and_edge_are_exported_and_planned_for_vessel() -> None:
    trace_store, data_store, time_bundle_id = _store_with_capsules(
        [_sample_capsule("turn_order_166_export_a")],
        batch_id="batch_order_166_export_core",
    )
    result = run_night_summarize_time_bundle(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_166",
        target_time_bundle_node_id=time_bundle_id,
        summary_run_id="001",
        adapter=SummaryPayloadAdapter({"summary_text": "One raw capsule coordinate record."}),
    )

    export = record_graph_memory_export_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_166_export",
        batch_id="batch_order_166_export",
    )

    assert result.summary_graph_node_data_id in export.packet.graph_node_data_ids
    assert result.summary_edge_data_id in export.packet.graph_edge_data_ids

    plan = record_graph_vessel_write_plan(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_166_plan",
        export_packet_id=export.packet.packet_id,
    )
    operations_by_source = {
        operation.source_data_id: operation.operation_kind
        for operation in plan.plan.operations
    }
    assert operations_by_source[result.summary_graph_node_data_id or ""] == (
        "upsert_graph_node"
    )
    assert operations_by_source[result.summary_edge_data_id or ""] == (
        "upsert_graph_edge"
    )


def _store_with_capsules(
    capsules: list[TurnStateCapsule],
    *,
    batch_id: str,
) -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_166_graph",
        batch_id=batch_id,
        capsules=capsules,
    )
    time_bundle_records = [
        record
        for record in data_store.list_records()
        if record.data_type == "graph_memory:node:time_bundle"
    ]
    assert len(time_bundle_records) == 1
    return trace_store, data_store, time_bundle_records[0].data_id


def _sample_capsule(turn_id: str) -> TurnStateCapsule:
    return TurnStateCapsule(
        turn_id=turn_id,
        node_movements=[
            NodeMovement(
                movement_id=f"move:{turn_id}:001",
                turn_id=turn_id,
                step_index=1,
                node_id="node_0",
                mode="pre_route_report",
                input_trace_ids=[f"trace:{turn_id}:user"],
                output_trace_ids=[f"trace:{turn_id}:node0"],
                status="completed",
            )
        ],
        trace_event_ids=[
            f"trace:{turn_id}:user",
            f"trace:{turn_id}:node0",
            f"trace:{turn_id}:final",
        ],
        user_input_trace_id=f"trace:{turn_id}:user",
        final_response_trace_id=f"trace:{turn_id}:final",
    )
