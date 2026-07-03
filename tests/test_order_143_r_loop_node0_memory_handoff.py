from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import (
    TIME_AXIS_NODE_ID,
    build_graph_memory_snapshot_from_capsules,
)
from songryeon_core.core.schemas import NodeMovement, TurnStateCapsule
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.nodes.node_0_memory_supplier import (
    build_r_loop_memory_handoff_packet_frame,
    record_r_loop_memory_handoff_packet,
)
from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.terminal_view import render_runtime_view


def test_node0_r_loop_handoff_preserves_graph_guide_coordinates() -> None:
    guide = _guide()
    frame = build_r_loop_memory_handoff_packet_frame(
        guide_packet=guide,
        source_trace_ids=["trace:graph_memory_builder"],
        source_data_ids=[guide.packet_id, guide.graph_snapshot_id],
    )

    assert frame.packet_status == "available"
    assert frame.target == "R_LOOP"
    assert frame.mode == "graph_guide_handoff"
    assert frame.r_loop_graph_guide_packet_id == guide.packet_id
    assert frame.graph_snapshot_id == guide.graph_snapshot_id
    assert frame.available_entry_node_ids == [TIME_AXIS_NODE_ID]
    assert frame.node_kind_counts == guide.node_kind_counts
    assert frame.summary_depth_range == guide.summary_depth_range
    assert frame.source_graph_node_ids == guide.source_graph_node_ids
    assert guide.packet_id in frame.source_data_ids
    assert guide.graph_snapshot_id in frame.source_data_ids
    assert frame.generated_by == "CODE:node_0_memory_supplier"
    assert frame.info_class == "absolute"
    assert frame.semantic_judgement_status == "not_run"


def test_node0_r_loop_handoff_records_trace_and_data_store_frame() -> None:
    guide = _guide()
    trace_store = TraceStore()
    data_store = DataStore()

    trace_id, data_id, frame = record_r_loop_memory_handoff_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_143",
        guide_packet=guide,
        input_ref=["trace:graph_memory_builder"],
        source_data_ids=[guide.packet_id, guide.graph_snapshot_id],
    )

    record = data_store.require_record(data_id)
    event = trace_store.get_event(trace_id)
    assert event is not None
    assert event.actor == "node_0"
    assert event.event_type == "memory_packet"
    assert record.data_type == "node_output:r_loop_memory_handoff_packet_frame"
    assert record.payload["packet_id"] == frame.packet_id
    assert record.payload["r_loop_graph_guide_packet_id"] == guide.packet_id


def test_node0_r_loop_handoff_missing_guide_closes_without_semantic_fallback() -> None:
    frame = build_r_loop_memory_handoff_packet_frame(
        guide_packet=None,
        source_trace_ids=["trace:no_guide"],
        source_data_ids=[],
    )

    assert frame.packet_status == "missing"
    assert frame.r_loop_graph_guide_packet_id == ""
    assert frame.graph_snapshot_id == ""
    assert frame.available_entry_node_ids == []
    assert frame.source_graph_node_ids == []
    assert frame.semantic_hint_status == "not_run"
    assert frame.semantic_judgement_status == "not_run"
    assert frame.info_class == "absolute"


def test_dry_run_records_r_loop_handoff_without_node1_or_node3_injection() -> None:
    result = run_dry_turn()
    handoff_id = result["r_loop_memory_handoff_packet_id"]
    guide_id = result["rloop_graph_guide_packet_id"]
    snapshot_id = result["graph_memory_snapshot_id"]

    assert result["r_loop_memory_handoff_status"] == "available"
    assert result["r_loop_memory_handoff_target"] == "R_LOOP"
    assert result["r_loop_memory_handoff_mode"] == "graph_guide_handoff"
    assert result["r_loop_memory_handoff_guide_packet_id"] == guide_id
    assert result["r_loop_memory_handoff_entry_node_count"] == 1
    assert result["r_loop_memory_handoff_semantic_hint_status"] == "not_run"
    assert result["r_loop_memory_handoff_info_class"] == "absolute"
    assert result["r_loop_memory_handoff_semantic_judgement_status"] == "not_run"

    records = result["data_records"]
    handoff_records = [
        record
        for record in records
        if record["data_type"] == "node_output:r_loop_memory_handoff_packet_frame"
    ]
    assert len(handoff_records) == 1
    assert handoff_records[0]["data_id"] == handoff_id
    assert guide_id in handoff_records[0]["payload"]["source_data_ids"]
    assert snapshot_id in handoff_records[0]["payload"]["source_data_ids"]

    for record in records:
        if record["data_type"] not in {"node_output:routing_decision", "node_output:report"}:
            continue
        source_data_ids = record["payload"].get("source_data_ids", [])
        assert handoff_id not in source_data_ids
        assert guide_id not in source_data_ids


def test_runtime_view_displays_r_loop_handoff_status_only() -> None:
    result = run_dry_turn()
    rendered = render_runtime_view(result, user_input="R handoff smoke")

    assert "- R loop memory handoff:" in rendered
    assert "status=available" in rendered
    assert "target=R_LOOP" in rendered
    assert "entry_nodes=1" in rendered
    assert "semantic_hint_status=not_run" in rendered


def _guide():
    build = build_graph_memory_snapshot_from_capsules(
        capsules=[_sample_capsule()],
        batch_id="batch_order_143",
    )
    return build.guide_packet


def _sample_capsule(turn_id: str = "turn_order_143_previous") -> TurnStateCapsule:
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
