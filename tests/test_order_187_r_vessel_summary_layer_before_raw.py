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
    _time_bundle_row,
)
from tests.test_order_184_r_vessel_multi_step_traversal import (
    SOURCE_KIND_ID,
    _source_kind_row,
)


RAW_SOURCE_ID = "graph:raw_source:internal_document:order_187"
SECOND_RAW_SOURCE_ID = "graph:raw_source:internal_document:order_187_b"
TOKEN_SUMMARY_ID = "graph:summary:token_budget_bundle:order_187"
LEAF_SUMMARY_ID = "graph:summary:source_leaf:order_187"
TOKEN_BUNDLE_ID = "graph:token_budget_summary_bundle:order_187:0001"


def test_source_kind_traversal_prefers_token_summary_layer_before_raw_source() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_187_packet",
        batch_id="order_187_packet",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
                _time_bundle_row(),
                _source_kind_row(
                    source_graph_node_ids=[RAW_SOURCE_ID, SECOND_RAW_SOURCE_ID],
                ),
                _raw_source_row(RAW_SOURCE_ID),
                _raw_source_row(SECOND_RAW_SOURCE_ID),
            ],
            summary_rows=[
                _source_leaf_summary_row(),
                _token_budget_summary_row(),
            ],
        ),
    )

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_187_traverse",
        user_question="source kind 아래에서 raw보다 token summary layer를 먼저 봐",
        read_packet=recorded.packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_187_traverse",
        input_ref=[recorded.trace_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.step_count == 4
    assert result.result_frame.selected_graph_node_ids == [
        "graph:axis:time",
        "graph:source_ingest_time_bundle:night_changed_sources",
        SOURCE_KIND_ID,
        TOKEN_SUMMARY_ID,
    ]
    assert RAW_SOURCE_ID not in result.result_frame.selected_graph_node_ids
    assert result.result_frame.final_graph_node_id == TOKEN_SUMMARY_ID
    assert result.result_frame.terminal_material_seen_count == 1
    assert result.result_frame.final_continuation_status == "stop_sufficient"


def test_source_kind_traversal_uses_leaf_summary_before_raw_when_token_layer_absent() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_187_leaf_packet",
        batch_id="order_187_leaf_packet",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
                _time_bundle_row(),
                _source_kind_row(source_graph_node_ids=[RAW_SOURCE_ID]),
                _raw_source_row(RAW_SOURCE_ID),
            ],
            summary_rows=[_source_leaf_summary_row()],
        ),
    )

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_187_leaf_traverse",
        user_question="source kind 아래에서 leaf summary를 먼저 봐",
        read_packet=recorded.packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_187_leaf_traverse",
        input_ref=[recorded.trace_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.selected_graph_node_ids == [
        "graph:axis:time",
        "graph:source_ingest_time_bundle:night_changed_sources",
        SOURCE_KIND_ID,
        LEAF_SUMMARY_ID,
    ]
    assert RAW_SOURCE_ID not in result.result_frame.selected_graph_node_ids
    assert result.result_frame.final_graph_node_id == LEAF_SUMMARY_ID


def _raw_source_row(raw_source_id: str) -> dict[str, object]:
    return {
        "candidate_node_id": raw_source_id,
        "display_name": "Raw Source: internal_document",
        "node_kind": "raw_source",
        "data_kind": "internal_document",
        "created_at": "2026-07-02T14:02:36",
        "written_at": "2026-07-02T14:02:36",
        "source_trace_id": None,
        "payload_json": json.dumps(
            {
                "node_kind": "raw_source",
                "data_kind": "internal_document",
                "summary_depth": 0,
                "source_leaf_count": 1,
                "source_summary_count": 0,
            },
            ensure_ascii=False,
        ),
        "labels": ["VesselRecord", "GraphMemoryNode", "RawSource"],
        "parent_graph_node_ids": [SOURCE_KIND_ID],
    }


def _source_leaf_summary_row() -> dict[str, object]:
    return {
        "summary_node_id": LEAF_SUMMARY_ID,
        "summary_display_name": "Summary: order_187 raw source",
        "data_kind": "source_leaf_summary",
        "info_class": "relative",
        "generated_by": "LLM:fake:night_summarize_source_leaf",
        "payload_json": json.dumps(
            {
                "data_kind": "source_leaf_summary",
                "summary_depth": 1,
                "summary_status": "ran",
                "validity_status": "active",
                "review_status": "not_reviewed",
                "target_graph_node_id": RAW_SOURCE_ID,
                "target_node_kind": "raw_source",
                "source_leaf_count": 1,
                "source_summary_count": 0,
                "source_graph_node_ids": [RAW_SOURCE_ID],
                "source_data_ids": [RAW_SOURCE_ID],
                "source_trace_ids": ["trace:summary:order_187_leaf"],
                "info_class": "relative",
                "generated_by": "LLM:fake:night_summarize_source_leaf",
                "summary_text": "Leaf summary for the ORDER 187 raw source.",
            },
            ensure_ascii=False,
        ),
        "target_graph_node_id": RAW_SOURCE_ID,
        "target_display_name": "Raw Source: internal_document",
        "target_node_kind": "raw_source",
    }


def _token_budget_summary_row() -> dict[str, object]:
    return {
        "summary_node_id": TOKEN_SUMMARY_ID,
        "summary_display_name": "Summary: token budget bundle order_187",
        "data_kind": "token_budget_bundle_summary",
        "info_class": "mixed",
        "generated_by": "LLM:fake:night_summarize_token_budget_bundle",
        "payload_json": json.dumps(
            {
                "data_kind": "token_budget_bundle_summary",
                "summary_depth": 2,
                "summary_status": "ran",
                "validity_status": "active",
                "review_status": "not_reviewed",
                "target_graph_node_id": TOKEN_BUNDLE_ID,
                "target_node_kind": "token_budget_summary_bundle",
                "source_leaf_count": 2,
                "source_summary_count": 1,
                "source_graph_node_ids": [TOKEN_BUNDLE_ID, LEAF_SUMMARY_ID],
                "source_data_ids": [
                    TOKEN_BUNDLE_ID,
                    LEAF_SUMMARY_ID,
                    RAW_SOURCE_ID,
                    SECOND_RAW_SOURCE_ID,
                ],
                "source_trace_ids": ["trace:summary:order_187_token"],
                "info_class": "mixed",
                "generated_by": "LLM:fake:night_summarize_token_budget_bundle",
                "summary_text": "Token budget bundle summary for the ORDER 187 raw source set.",
            },
            ensure_ascii=False,
        ),
        "target_graph_node_id": TOKEN_BUNDLE_ID,
        "target_display_name": "Token Budget Summary Bundle",
        "target_node_kind": "token_budget_summary_bundle",
    }
