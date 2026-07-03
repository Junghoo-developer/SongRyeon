from __future__ import annotations

from songryeon_core.core.r_loop_vessel_continuation_checkpoint import (
    R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_DATA_TYPE,
    R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_GENERATOR,
)
from songryeon_core.loops.r_loop_vessel_one_step import (
    RLoopVesselTraverseFakeLLMAdapter,
    run_r_loop_vessel_traverse,
)
from songryeon_core.runtime.r_loop_vessel_one_step import (
    render_r_loop_vessel_traverse_text,
    run_local_r_loop_vessel_traverse,
)

from tests.test_order_175_vessel_backed_r_read_packet import (
    FakeRLoopVesselDriverFactory,
)
from tests.test_order_184_r_vessel_multi_step_traversal import (
    SOURCE_INGEST_ID,
    SOURCE_KIND_ID,
    SUMMARY_ID,
    _record_packet,
    _source_ingest_row,
    _source_kind_row,
    _summary_row,
    _time_axis_row,
)


def test_continue_deeper_records_node0_checkpoint_per_continuation_step() -> None:
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
        turn_id="turn_order_197_checkpoint",
        user_question="중간 체크포인트를 남기며 내려가",
        read_packet=packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_197_checkpoint",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.selected_graph_node_ids == [
        "graph:axis:time",
        SOURCE_INGEST_ID,
        SOURCE_KIND_ID,
        SUMMARY_ID,
    ]
    assert len(result.continuation_checkpoints) == 3
    assert [frame.step_index for frame in result.continuation_checkpoints] == [1, 2, 3]
    assert [frame.next_candidate_graph_node_ids for frame in result.continuation_checkpoints] == [
        [SOURCE_INGEST_ID],
        [SOURCE_KIND_ID],
        [SUMMARY_ID],
    ]
    assert result.continuation_checkpoints[0].selected_graph_node_ids_so_far == [
        "graph:axis:time"
    ]
    assert result.continuation_checkpoints[-1].inspected_graph_node_ids_so_far == [
        "graph:axis:time",
        SOURCE_INGEST_ID,
        SOURCE_KIND_ID,
    ]
    for frame in result.continuation_checkpoints:
        assert frame.generated_by == R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_GENERATOR
        assert frame.info_class == "absolute"
        assert frame.semantic_judgement_status == "not_run"
        assert frame.continuation_status == "continue_deeper"
        assert frame.next_target_node == "R2"
        record = data_store.require_record(frame.packet_id)
        assert record.data_type == R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_DATA_TYPE


def test_stop_condition_does_not_create_fake_checkpoint() -> None:
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
        turn_id="turn_order_197_stop",
        user_question="예산이 끝나면 가짜 체크포인트를 만들지 마",
        read_packet=packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_197_stop",
        input_ref=[packet_event_id],
        max_node_reads=1,
        max_traversal_depth=1,
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.final_continuation_status == "stop_budget_exhausted"
    assert result.continuation_checkpoints == []
    assert [
        record.data_type
        for record in data_store.list_records()
        if record.data_type == R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_DATA_TYPE
    ] == []


def test_activity_ledger_includes_r_vessel_continuation_checkpoints() -> None:
    runtime_result = run_local_r_loop_vessel_traverse(
        user_question="R checkpoint 장부 표시를 확인해",
        batch_id="order_197_local",
        turn_id="turn_order_197_local",
        database="neo4j",
        allow_no_auth=True,
        llm_mode="fake",
        driver_factory_for_test=FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
                _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
            ],
            summary_rows=[_summary_row()],
        ),
    )

    assert runtime_result["r_vessel_checkpoint_count"] == 3
    assert runtime_result["r_vessel_checkpoint_latest_step"] == 3
    assert runtime_result["r_vessel_checkpoint_latest_next_candidate_count"] == 1
    ledger = runtime_result["activity_ledger_frame"]
    assert isinstance(ledger, dict)
    assert len(ledger["continuation_checkpoint_packet_ids"]) == 3
    assert any(
        record["stage"] == "continuation_checkpoint"
        for record in ledger["activity_records"]
    )
    rendered = render_r_loop_vessel_traverse_text(runtime_result)
    assert "R Vessel checkpoints: count=3 / latest_step=3 / next_candidates=1" in rendered
