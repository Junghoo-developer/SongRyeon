import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import record_r_loop_vessel_read_packet
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.r_loop_vessel_one_step import (
    R_TRAVERSE_MAX_RAW_ORIGINAL_MATERIAL_READS,
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
from tests.test_order_187_r_vessel_summary_layer_before_raw import (
    _source_leaf_summary_row,
    _token_budget_summary_row,
)


def test_r_vessel_traverse_stops_after_five_raw_original_reads() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    raw_ids = [f"graph:raw_source:internal_document:order_188_{index}" for index in range(1, 7)]
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_188_packet",
        batch_id="order_188_packet",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
                _time_bundle_row(),
                _source_kind_row(source_graph_node_ids=[raw_ids[0]]),
                *[
                    _raw_source_chain_row(
                        raw_id=raw_id,
                        next_raw_id=raw_ids[index + 1] if index + 1 < len(raw_ids) else None,
                        parent_id=SOURCE_KIND_ID if index == 0 else raw_ids[index - 1],
                    )
                    for index, raw_id in enumerate(raw_ids)
                ],
            ],
            summary_rows=[],
        ),
    )

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_188_traverse",
        user_question="raw source 원본을 많이 내려가려고 해도 최대 5회까지만 봐",
        read_packet=recorded.packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_188_traverse",
        input_ref=[recorded.trace_event_id],
        max_node_reads=12,
        max_traversal_depth=12,
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.raw_original_material_seen_count == 5
    assert result.result_frame.max_raw_original_material_count == (
        R_TRAVERSE_MAX_RAW_ORIGINAL_MATERIAL_READS
    )
    assert result.result_frame.raw_original_read_cap_reached is True
    assert result.result_frame.final_continuation_status == "stop_budget_exhausted"
    assert result.continuations[-1].continuation_reason_code == (
        "CODE_STATUS:r_loop_raw_original_read_cap_reached"
    )
    assert raw_ids[:5] == result.result_frame.selected_graph_node_ids[-5:]
    assert raw_ids[5] not in result.result_frame.selected_graph_node_ids


def test_summary_layer_material_does_not_count_as_raw_original_read() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    raw_id = "graph:raw_source:internal_document:order_187"
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_188_summary_packet",
        batch_id="order_188_summary_packet",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
                _time_bundle_row(),
                _source_kind_row(source_graph_node_ids=[raw_id]),
                _raw_source_chain_row(raw_id=raw_id, next_raw_id=None, parent_id=SOURCE_KIND_ID),
            ],
            summary_rows=[_source_leaf_summary_row(), _token_budget_summary_row()],
        ),
    )

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_188_summary_traverse",
        user_question="summary layer를 먼저 보면 원본 열람으로 세지 않아야 해",
        read_packet=recorded.packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_188_summary_traverse",
        input_ref=[recorded.trace_event_id],
    )

    assert result.result_frame.raw_original_material_seen_count == 0
    assert result.result_frame.raw_original_read_cap_reached is False


def _raw_source_chain_row(
    *,
    raw_id: str,
    next_raw_id: str | None,
    parent_id: str,
) -> dict[str, object]:
    return {
        "candidate_node_id": raw_id,
        "display_name": "Raw Source: internal_document",
        "node_kind": "raw_source",
        "data_kind": "internal_document",
        "created_at": "2026-07-03T00:00:00",
        "written_at": "2026-07-03T00:00:00",
        "source_trace_id": None,
        "payload_json": json.dumps(
            {
                "node_kind": "raw_source",
                "data_kind": "internal_document",
                "summary_depth": 0,
                "source_leaf_count": 1,
                "source_summary_count": 0,
                "source_graph_node_ids": [next_raw_id] if next_raw_id else [],
            },
            ensure_ascii=False,
        ),
        "labels": ["VesselRecord", "GraphMemoryNode", "RawSource"],
        "parent_graph_node_ids": [parent_id],
    }
