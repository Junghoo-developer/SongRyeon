import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import record_r_loop_vessel_read_packet
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.r_loop_vessel_one_step import (
    RLoopVesselTraverseFakeLLMAdapter,
    run_r_loop_vessel_traverse,
)

from tests.test_order_175_vessel_backed_r_read_packet import (
    READ_AT,
    FakeRLoopVesselDriverFactory,
    _config,
)
from tests.test_order_183_r_vessel_hierarchical_child_surface import (
    _source_ingest_row,
    _time_axis_row,
)


SOURCE_INGEST_ID = "graph:source_ingest_time_bundle:night_changed_sources"
SOURCE_KIND_ID = "graph:source_kind_bundle:batch:code"
SUMMARY_ID = "graph:summary:source_kind:code_bundle"


def test_r_vessel_traverse_descends_from_core_ego_to_summary() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet(
        entry_rows=[
            _time_axis_row(),
            _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
            _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
        ],
        summary_rows=[_summary_row()],
    )

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_184_traverse",
        user_question="CoreEgo에서 source kind summary까지 계층적으로 내려가",
        read_packet=packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_184_traverse",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.step_count == 4
    assert result.result_frame.selected_graph_node_ids == [
        "graph:axis:time",
        SOURCE_INGEST_ID,
        SOURCE_KIND_ID,
        SUMMARY_ID,
    ]
    assert result.result_frame.final_graph_node_id == SUMMARY_ID
    assert result.result_frame.final_sufficiency_status == "sufficient"
    assert result.result_frame.final_continuation_status == "stop_sufficient"
    assert result.result_frame.r_loop_task_status == "sufficient"
    assert result.result_frame.terminal_material_seen_count == 1
    assert result.result_frame.min_terminal_material_count == 1
    assert result.result_frame.early_stop_guard_trigger_count == 0
    assert len(result.candidate_layer_surfaces) == 4
    assert len(result.graph_traversal_candidate_surfaces) == 4
    assert len(result.r2_selections) == 4
    assert len(result.r3_inspections) == 4
    stored = data_store.require_record(result.result_frame.frame_id)
    assert stored.data_type == "r_loop:vessel_traverse_result"


def test_r_vessel_traverse_stops_when_budget_runs_out_before_summary() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet(
        entry_rows=[
            _time_axis_row(),
            _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
            _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
        ],
        summary_rows=[_summary_row()],
    )

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_184_budget",
        user_question="예산이 작으면 중간에서 멈춰야 한다",
        read_packet=packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_184_budget",
        input_ref=[packet_event_id],
        max_node_reads=2,
        max_traversal_depth=2,
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.step_count == 2
    assert result.result_frame.final_graph_node_id == SOURCE_INGEST_ID
    assert result.result_frame.final_sufficiency_status == "insufficient"
    assert result.result_frame.final_continuation_status == "stop_budget_exhausted"
    assert result.result_frame.r_loop_task_status == "partial"


def _record_packet(
    *,
    entry_rows: list[dict[str, object]],
    summary_rows: list[dict[str, object]],
):
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_184_packet",
        batch_id="order_184_packet",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=entry_rows,
            summary_rows=summary_rows,
        ),
    )
    return trace_store, data_store, recorded.trace_event_id, recorded.packet


def _source_kind_row(*, source_graph_node_ids: list[str]) -> dict[str, object]:
    return {
        "candidate_node_id": SOURCE_KIND_ID,
        "display_name": "Source Kind Bundle: code",
        "node_kind": "source_kind_bundle",
        "data_kind": "code_bundle",
        "created_at": "2026-07-02T14:02:36",
        "written_at": "2026-07-02T14:02:36",
        "source_trace_id": None,
        "payload_json": json.dumps(
            {
                "node_kind": "source_kind_bundle",
                "data_kind": "code_bundle",
                "summary_depth": 0,
                "source_leaf_count": 1,
                "source_summary_count": 0,
                "source_graph_node_ids": source_graph_node_ids,
            },
            ensure_ascii=False,
        ),
        "labels": ["VesselRecord", "GraphMemoryNode", "SourceKindBundle"],
        "parent_graph_node_ids": [SOURCE_INGEST_ID],
    }


def _summary_row() -> dict[str, object]:
    return {
        "summary_node_id": SUMMARY_ID,
        "summary_display_name": "Summary: code source kind bundle",
        "data_kind": "source_kind_summary",
        "info_class": "mixed",
        "generated_by": "LLM:fake:night_summarize_token_layer",
        "payload_json": json.dumps(
            {
                "data_kind": "source_kind_summary",
                "summary_depth": 1,
                "summary_status": "ran",
                "validity_status": "active",
                "review_status": "not_reviewed",
                "target_graph_node_id": SOURCE_KIND_ID,
                "target_node_kind": "source_kind_bundle",
                "source_leaf_count": 3,
                "source_summary_count": 0,
                "source_graph_node_ids": [SOURCE_KIND_ID],
                "source_data_ids": [SOURCE_KIND_ID],
                "source_trace_ids": ["trace:summary:active"],
                "info_class": "mixed",
                "generated_by": "LLM:fake:night_summarize_token_layer",
                "summary_text": "Code source kind bundle summary for R traversal.",
            },
            ensure_ascii=False,
        ),
        "target_graph_node_id": SOURCE_KIND_ID,
        "target_display_name": "Source Kind Bundle: code",
        "target_node_kind": "source_kind_bundle",
    }
