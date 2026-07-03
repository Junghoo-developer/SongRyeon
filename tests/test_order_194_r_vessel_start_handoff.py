from __future__ import annotations

from dataclasses import replace

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_start_handoff import (
    R_LOOP_VESSEL_START_HANDOFF_DATA_TYPE,
    R_LOOP_VESSEL_START_HANDOFF_GENERATOR,
    record_r_loop_vessel_start_handoff_packet,
)
from songryeon_core.core.trace_store import TraceStore
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


def test_node0_records_vessel_r_start_handoff_from_passed_read_packet() -> None:
    trace_store, data_store, read_event_id, read_packet = _record_packet()

    recorded = record_r_loop_vessel_start_handoff_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_194",
        batch_id="order_194_start",
        read_packet=read_packet,
        source_read_packet_trace_event_id=read_event_id,
        recent_turn_capsule_count=3,
        recent_raw_conversation_count=2,
    )

    assert recorded.packet.packet_status == "available"
    assert recorded.packet.target == "R_LOOP"
    assert recorded.packet.mode == "vessel_r_start_handoff"
    assert recorded.packet.source_vessel_read_packet_id == read_packet.packet_id
    assert recorded.packet.entry_candidate_count == read_packet.entry_candidate_count
    assert recorded.packet.summary_candidate_count == read_packet.summary_candidate_count
    assert recorded.packet.available_entry_node_ids
    assert recorded.packet.recent_turn_capsule_count == 3
    assert recorded.packet.recent_raw_conversation_count == 2
    assert recorded.packet.generated_by == R_LOOP_VESSEL_START_HANDOFF_GENERATOR
    assert recorded.packet.info_class == "absolute"
    assert recorded.packet.semantic_judgement_status == "not_run"

    event = trace_store.get_event(recorded.trace_event_id)
    assert event is not None
    assert event.actor == "node_0"
    assert event.event_type == "memory_packet"
    assert recorded.packet.packet_id in event.output_ref

    stored = data_store.require_record(recorded.packet.packet_id)
    assert stored.data_type == R_LOOP_VESSEL_START_HANDOFF_DATA_TYPE


def test_node0_handoff_preserves_failed_read_packet_without_fake_candidates() -> None:
    trace_store, data_store, read_event_id, read_packet = _record_packet()
    failed_packet = replace(
        read_packet,
        read_status="read_failed",
        failure_type="neo4j_read_failed",
        failure_reason="boom",
        entry_candidate_count=0,
        summary_candidate_count=0,
        entry_candidate_records=[],
        summary_candidate_records=[],
        source_data_ids=[],
        source_trace_ids=[],
    )

    recorded = record_r_loop_vessel_start_handoff_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_194_failed",
        batch_id="order_194_failed_start",
        read_packet=failed_packet,
        source_read_packet_trace_event_id=read_event_id,
    )

    assert recorded.packet.packet_status == "read_failed"
    assert recorded.packet.available_entry_node_ids == []
    assert recorded.packet.entry_candidate_count == 0
    assert recorded.packet.summary_candidate_count == 0
    assert recorded.packet.source_vessel_read_packet_id == failed_packet.packet_id


def test_vessel_r_traverse_result_sources_include_node0_start_handoff() -> None:
    trace_store, data_store, read_event_id, read_packet = _record_packet()
    handoff = record_r_loop_vessel_start_handoff_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_194_traverse",
        batch_id="order_194_traverse_start",
        read_packet=read_packet,
        source_read_packet_trace_event_id=read_event_id,
    )

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_194_traverse",
        user_question="R 시작 handoff source id를 보존해",
        read_packet=read_packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_194_traverse",
        input_ref=[read_event_id, handoff.trace_event_id],
        start_handoff_packet_id=handoff.packet.packet_id,
    )

    assert result.result_frame.traverse_status == "completed"
    assert handoff.packet.packet_id in result.result_frame.source_data_ids
    assert handoff.trace_event_id in result.result_frame.source_trace_ids


def test_local_vessel_r_traverse_records_and_renders_start_handoff() -> None:
    result = run_local_r_loop_vessel_traverse(
        user_question="0 start handoff 표시를 확인해",
        batch_id="order_194_local",
        turn_id="turn_order_194_local",
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

    assert result["start_handoff_packet_status"] == "available"
    assert isinstance(result["start_handoff_packet_id"], str)
    assert result["start_handoff_packet_id"]
    assert result["start_handoff_packet_id"] in result["result_frame"]["source_data_ids"]
    rendered = render_r_loop_vessel_traverse_text(result)
    assert "node_0 Vessel R start handoff: status=available" in rendered


def _record_packet():
    trace_store = TraceStore()
    data_store = DataStore()
    from songryeon_core.core.r_loop_vessel_read_packet import record_r_loop_vessel_read_packet

    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_194_packet",
        batch_id="order_194_packet",
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
