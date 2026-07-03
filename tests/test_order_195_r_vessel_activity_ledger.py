from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import record_r_loop_vessel_read_packet
from songryeon_core.core.r_loop_vessel_start_handoff import (
    record_r_loop_vessel_start_handoff_packet,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.r_loop_vessel_activity_ledger import (
    R_LOOP_VESSEL_ACTIVITY_LEDGER_DATA_TYPE,
    R_LOOP_VESSEL_ACTIVITY_LEDGER_GENERATOR,
    record_r_loop_vessel_activity_ledger,
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
    READ_AT,
    FakeRLoopVesselDriverFactory,
    _config,
)
from tests.test_order_184_r_vessel_multi_step_traversal import (
    SOURCE_KIND_ID,
    _source_ingest_row,
    _source_kind_row,
    _summary_row,
    _time_axis_row,
)


def test_r_vessel_activity_ledger_records_successful_traverse_frames() -> None:
    trace_store, data_store, read_event_id, read_packet = _record_packet()
    handoff = record_r_loop_vessel_start_handoff_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_195",
        batch_id="order_195_start",
        read_packet=read_packet,
        source_read_packet_trace_event_id=read_event_id,
    )
    run = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_195",
        user_question="R 활동 장부를 만들어",
        read_packet=read_packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_195_success",
        input_ref=[read_event_id, handoff.trace_event_id],
        start_handoff_packet_id=handoff.packet.packet_id,
    )

    trace_id, frame_id, ledger = record_r_loop_vessel_activity_ledger(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_195",
        traverse_run=run,
        frame_label="order_195_success",
        source_start_handoff_packet_id=handoff.packet.packet_id,
    )

    assert ledger.generated_by == R_LOOP_VESSEL_ACTIVITY_LEDGER_GENERATOR
    assert ledger.info_class == "absolute"
    assert ledger.semantic_judgement_status == "not_run"
    assert ledger.source_start_handoff_packet_id == handoff.packet.packet_id
    assert ledger.source_read_packet_id == read_packet.packet_id
    assert ledger.traverse_result_frame_id == run.result_frame.frame_id
    assert ledger.traverse_status == "completed"
    assert ledger.r_loop_task_status == run.result_frame.r_loop_task_status
    assert ledger.final_continuation_status == run.result_frame.final_continuation_status
    assert ledger.selected_graph_node_ids == run.result_frame.selected_graph_node_ids
    assert ledger.inspected_graph_node_ids == run.result_frame.inspected_graph_node_ids
    assert ledger.r1_goal_frame_id == run.r1_goal.frame_id
    assert ledger.r2_selection_frame_ids == [frame.frame_id for frame in run.r2_selections]
    assert ledger.r3_inspection_frame_ids == [frame.frame_id for frame in run.r3_inspections]
    assert ledger.continuation_frame_ids == [frame.frame_id for frame in run.continuations]
    assert ledger.return_summary_frame_id == run.return_summary.frame_id
    assert ledger.budget_frame_ids
    assert ledger.candidate_graph_node_ids
    assert data_store.get_record(frame_id) is not None
    assert trace_store.get_event(trace_id) is not None
    stored = data_store.require_record(frame_id)
    assert stored.data_type == R_LOOP_VESSEL_ACTIVITY_LEDGER_DATA_TYPE


def test_r_vessel_activity_ledger_preserves_failed_traverse() -> None:
    trace_store, data_store, read_event_id, read_packet = _record_packet()
    handoff = record_r_loop_vessel_start_handoff_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_195_failed",
        batch_id="order_195_failed_start",
        read_packet=read_packet,
        source_read_packet_trace_event_id=read_event_id,
    )
    run = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_195_failed",
        user_question="adapter 실패도 장부에 남겨",
        read_packet=read_packet,
        adapter=None,
        frame_label="order_195_failed",
        input_ref=[read_event_id, handoff.trace_event_id],
        start_handoff_packet_id=handoff.packet.packet_id,
    )

    _, _, ledger = record_r_loop_vessel_activity_ledger(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_195_failed",
        traverse_run=run,
        frame_label="order_195_failed",
        source_start_handoff_packet_id=handoff.packet.packet_id,
    )

    assert ledger.traverse_status == "failed"
    assert ledger.failure_stage == "adapter"
    assert ledger.failure_type == "adapter_missing"
    assert ledger.r1_goal_frame_id is None
    assert ledger.r2_selection_frame_ids == []
    assert ledger.r3_inspection_frame_ids == []
    assert ledger.source_start_handoff_packet_id == handoff.packet.packet_id
    assert ledger.traverse_result_frame_id == run.result_frame.frame_id
    assert any(record["stage"] == "traverse_result" for record in ledger.activity_records)


def test_local_vessel_r_traverse_records_and_renders_activity_ledger() -> None:
    result = run_local_r_loop_vessel_traverse(
        user_question="R 활동 장부 표시를 확인해",
        batch_id="order_195_local",
        turn_id="turn_order_195_local",
        database="neo4j",
        allow_no_auth=True,
        llm_mode="fake",
        driver_factory_for_test=FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
                _source_kind_row(source_graph_node_ids=[]),
            ],
            summary_rows=[_summary_row()],
        ),
    )

    assert result["activity_ledger_frame_id"]
    assert result["activity_ledger_task_status"] == result["r_loop_task_status"]
    assert result["activity_ledger_selected_count"] == len(result["selected_graph_node_ids"])
    assert result["activity_ledger_inspected_count"] == len(result["inspected_graph_node_ids"])
    assert result["activity_ledger_frame"]["source_start_handoff_packet_id"] == (
        result["start_handoff_packet_id"]
    )
    rendered = render_r_loop_vessel_traverse_text(result)
    assert "R Vessel activity ledger: status=" in rendered


def _record_packet():
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_195_packet",
        batch_id="order_195_packet",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
                _source_kind_row(source_graph_node_ids=[]),
            ],
            summary_rows=[_summary_row()],
        ),
    )
    return trace_store, data_store, recorded.trace_event_id, recorded.packet
