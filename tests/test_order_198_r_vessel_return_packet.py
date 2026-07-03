from __future__ import annotations

from songryeon_core.core.r_loop_vessel_return_packet import (
    R_LOOP_VESSEL_RETURN_PACKET_DATA_TYPE,
    R_LOOP_VESSEL_RETURN_PACKET_GENERATOR,
    record_r_loop_vessel_return_packet,
)
from songryeon_core.core.r_loop_vessel_start_handoff import (
    record_r_loop_vessel_start_handoff_packet,
)
from songryeon_core.core.schemas import MetainfoBoundary
from songryeon_core.loops.r_loop_vessel_activity_ledger import (
    record_r_loop_vessel_activity_ledger,
)
from songryeon_core.loops.r_loop_vessel_one_step import (
    RLoopVesselTraverseFakeLLMAdapter,
    run_r_loop_vessel_traverse,
)
from songryeon_core.nodes.node_2_handoff import record_node3_input_brief
from songryeon_core.runtime.r_loop_vessel_one_step import (
    render_r_loop_vessel_traverse_text,
    run_local_r_loop_vessel_traverse,
)

from tests.test_order_175_vessel_backed_r_read_packet import (
    FakeRLoopVesselDriverFactory,
)
from tests.test_order_184_r_vessel_multi_step_traversal import (
    SOURCE_KIND_ID,
    SUMMARY_ID,
    _record_packet,
    _source_ingest_row,
    _source_kind_row,
    _summary_row,
    _time_axis_row,
)


def test_successful_r_vessel_traverse_creates_node0_return_packet() -> None:
    trace_store, data_store, read_event_id, packet = _record_packet(
        entry_rows=[
            _time_axis_row(),
            _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
            _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
        ],
        summary_rows=[_summary_row()],
    )
    handoff = record_r_loop_vessel_start_handoff_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_198_success",
        batch_id="order_198_success_start",
        read_packet=packet,
        source_read_packet_trace_event_id=read_event_id,
    )
    run = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_198_success",
        user_question="R return packet 성공 케이스",
        read_packet=packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_198_success",
        input_ref=[read_event_id, handoff.trace_event_id],
        start_handoff_packet_id=handoff.packet.packet_id,
    )
    _, ledger_id, _ = record_r_loop_vessel_activity_ledger(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_198_success",
        traverse_run=run,
        frame_label="order_198_success",
        source_start_handoff_packet_id=handoff.packet.packet_id,
    )

    trace_id, return_packet_id, return_packet = _record_return_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_198_success",
        ledger_id=ledger_id,
        frame_label="order_198_success",
    )

    assert return_packet.generated_by == R_LOOP_VESSEL_RETURN_PACKET_GENERATOR
    assert return_packet.return_status == "available"
    assert return_packet.node3_material_ready is True
    assert return_packet.source_activity_ledger_frame_id == ledger_id
    assert return_packet.source_traverse_result_frame_id == run.result_frame.frame_id
    assert return_packet.source_return_summary_frame_id == run.return_summary.frame_id
    assert return_packet.source_read_packet_id == packet.packet_id
    assert return_packet.selected_graph_node_count == 4
    assert return_packet.inspected_graph_node_count == 4
    assert return_packet.summary_material_count == 1
    assert return_packet.raw_original_material_count == 0
    assert data_store.require_record(return_packet_id).data_type == (
        R_LOOP_VESSEL_RETURN_PACKET_DATA_TYPE
    )
    assert trace_store.get_event(trace_id) is not None


def test_failed_r_vessel_traverse_creates_failed_return_packet() -> None:
    trace_store, data_store, read_event_id, packet = _record_packet(
        entry_rows=[
            _time_axis_row(),
            _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
            _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
        ],
        summary_rows=[_summary_row()],
    )
    handoff = record_r_loop_vessel_start_handoff_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_198_failed",
        batch_id="order_198_failed_start",
        read_packet=packet,
        source_read_packet_trace_event_id=read_event_id,
    )
    run = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_198_failed",
        user_question="adapter 실패도 return packet으로 보존",
        read_packet=packet,
        adapter=None,
        frame_label="order_198_failed",
        input_ref=[read_event_id, handoff.trace_event_id],
        start_handoff_packet_id=handoff.packet.packet_id,
    )
    _, ledger_id, _ = record_r_loop_vessel_activity_ledger(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_198_failed",
        traverse_run=run,
        frame_label="order_198_failed",
        source_start_handoff_packet_id=handoff.packet.packet_id,
    )

    _, _, return_packet = _record_return_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_198_failed",
        ledger_id=ledger_id,
        frame_label="order_198_failed",
    )

    assert return_packet.return_status == "failed"
    assert return_packet.node3_material_ready is False
    assert return_packet.traverse_status == "failed"
    assert return_packet.failure_stage == "adapter"
    assert return_packet.failure_type == "adapter_missing"
    assert return_packet.summary_material_count == 0


def test_node3_brief_prefers_node0_return_packet_over_raw_traverse_result() -> None:
    trace_store, data_store, read_event_id, packet = _record_packet(
        entry_rows=[
            _time_axis_row(),
            _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
            _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
        ],
        summary_rows=[_summary_row()],
    )
    handoff = record_r_loop_vessel_start_handoff_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_198_brief",
        batch_id="order_198_brief_start",
        read_packet=packet,
        source_read_packet_trace_event_id=read_event_id,
    )
    run = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_198_brief",
        user_question="node_2는 return packet을 우선 봐",
        read_packet=packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_198_brief",
        input_ref=[read_event_id, handoff.trace_event_id],
        start_handoff_packet_id=handoff.packet.packet_id,
    )
    _, ledger_id, _ = record_r_loop_vessel_activity_ledger(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_198_brief",
        traverse_run=run,
        frame_label="order_198_brief",
        source_start_handoff_packet_id=handoff.packet.packet_id,
    )
    _, return_packet_id, _ = _record_return_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_198_brief",
        ledger_id=ledger_id,
        frame_label="order_198_brief",
    )

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_198_brief",
        user_question="R material source를 확인해줘",
        handoff_frame_id="node_2:handoff:order_198",
        boundary=MetainfoBoundary(),
        input_trace_ids=[read_event_id],
        source_data_ids=["node_2:handoff:order_198"],
    )

    assert brief.vessel_r_material is not None
    assert brief.vessel_r_material_status == "present"
    assert brief.vessel_r_material.source_data_id == return_packet_id
    assert return_packet_id in brief.vessel_r_material_source_data_ids
    assert run.result_frame.frame_id in brief.vessel_r_material_source_data_ids
    assert SUMMARY_ID in brief.vessel_r_material_source_data_ids


def test_order_193_direct_traverse_fallback_still_works_without_return_packet() -> None:
    trace_store, data_store, read_event_id, packet = _record_packet(
        entry_rows=[
            _time_axis_row(),
            _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
            _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
        ],
        summary_rows=[_summary_row()],
    )
    run = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_198_fallback",
        user_question="return packet이 없어도 기존 fallback은 유지",
        read_packet=packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_198_fallback",
        input_ref=[read_event_id],
    )

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_198_fallback",
        user_question="fallback source를 확인해줘",
        handoff_frame_id="node_2:handoff:order_198_fallback",
        boundary=MetainfoBoundary(),
        input_trace_ids=[read_event_id],
        source_data_ids=["node_2:handoff:order_198_fallback"],
    )

    assert brief.vessel_r_material is not None
    assert brief.vessel_r_material_status == "present"
    assert brief.vessel_r_material.source_data_id == run.result_frame.frame_id


def test_local_vessel_r_traverse_records_and_renders_return_packet() -> None:
    result = run_local_r_loop_vessel_traverse(
        user_question="R return packet runtime 표시를 확인해",
        batch_id="order_198_local",
        turn_id="turn_order_198_local",
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

    assert result["r_vessel_return_status"] == "available"
    assert result["r_vessel_return_node3_material_ready"] is True
    assert result["r_vessel_return_packet_id"]
    rendered = render_r_loop_vessel_traverse_text(result)
    assert "node_0 Vessel R return packet: status=available" in rendered


def _record_return_packet(
    *,
    trace_store,
    data_store,
    turn_id: str,
    ledger_id: str,
    frame_label: str,
):
    recorded = record_r_loop_vessel_return_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        activity_ledger_frame_id=ledger_id,
        frame_label=frame_label,
    )
    return recorded.trace_event_id, recorded.packet.packet_id, recorded.packet
