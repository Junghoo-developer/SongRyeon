from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import (
    R_LOOP_VESSEL_EXACT_CHILD_EXPANSION_POLICY_ID,
    build_r_loop_vessel_read_packet_from_neo4j,
    record_r_loop_vessel_read_packet,
)
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
    SUMMARY_ID,
    _source_kind_row,
    _summary_row,
)


def test_read_packet_expands_exact_child_records_outside_base_limit() -> None:
    packet = build_r_loop_vessel_read_packet_from_neo4j(
        config=_config(),
        batch_id="order_186_exact_child_packet",
        created_at=READ_AT,
        limit=3,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows_with_source_kind_outside_limit(),
            summary_rows=[_summary_row()],
        ),
    )

    entry_ids = [
        record["candidate_node_id"]
        for record in packet.entry_candidate_records
    ]

    assert packet.read_status == "passed"
    assert packet.exact_child_expansion_policy_id == (
        R_LOOP_VESSEL_EXACT_CHILD_EXPANSION_POLICY_ID
    )
    assert packet.base_entry_candidate_count == 3
    assert packet.exact_child_expanded_entry_count == 1
    assert packet.exact_child_expanded_node_ids == [SOURCE_KIND_ID]
    assert packet.exact_child_expansion_truncated is False
    assert entry_ids == [
        "graph:axis:time",
        "graph:source_ingest_time_bundle:night_changed_sources",
        "graph:time_bundle:manual_vessel_first_write:core",
        SOURCE_KIND_ID,
    ]


def test_traverse_can_descend_through_expanded_exact_child_record() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_186_packet",
        batch_id="order_186_traverse_packet",
        config=_config(),
        created_at=READ_AT,
        limit=3,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows_with_source_kind_outside_limit(),
            summary_rows=[_summary_row()],
        ),
    )

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_186_traverse",
        user_question="source ingest 아래 source kind와 summary까지 계층적으로 내려가",
        read_packet=recorded.packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_186_traverse",
        input_ref=[recorded.trace_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.step_count == 4
    assert result.result_frame.selected_graph_node_ids == [
        "graph:axis:time",
        "graph:source_ingest_time_bundle:night_changed_sources",
        SOURCE_KIND_ID,
        SUMMARY_ID,
    ]
    assert result.result_frame.final_graph_node_id == SUMMARY_ID
    assert result.result_frame.terminal_material_seen_count == 1
    assert result.result_frame.final_continuation_status == "stop_sufficient"


def _entry_rows_with_source_kind_outside_limit() -> list[dict[str, object]]:
    return [
        _time_axis_row(),
        _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
        _time_bundle_row(),
        _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
    ]
