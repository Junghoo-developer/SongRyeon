from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import (
    build_graph_memory_snapshot_from_capsules,
    raw_capsule_graph_node_id,
    record_graph_memory_for_capsules,
)
from songryeon_core.core.schemas import (
    NodeMovement,
    RLoopMemoryHandoffPacketFrame,
    TurnStateCapsule,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.r_loop_dry_run import run_r_loop_dry_run_skeleton
from songryeon_core.nodes.node_0_memory_supplier import record_r_loop_memory_handoff_packet


def test_candidate_surface_copies_child_candidates_from_r3_inspection() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    graph_record = record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_149_graph_build",
        capsules=[
            _sample_capsule("turn_order_149_child_001"),
            _sample_capsule("turn_order_149_child_002"),
        ],
        batch_id="batch_order_149_child",
    )
    handoff_trace_id, _handoff_data_id, handoff = record_r_loop_memory_handoff_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_149_runtime",
        guide_packet=graph_record.build.guide_packet,
        input_ref=[graph_record.trace_event_id],
        source_data_ids=[
            graph_record.build.snapshot.snapshot_id,
            graph_record.build.guide_packet.packet_id,
        ],
    )

    result = run_r_loop_dry_run_skeleton(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_149_runtime",
        handoff_packet=handoff,
        input_ref=[handoff_trace_id],
        frame_label="order_149_child",
    )

    surface = result.candidate_surfaces[0]
    record = data_store.require_record(surface.frame_id)

    assert record.data_type == "node_output:R_graph_traversal_candidate_surface_frame"
    assert surface.child_candidate_node_ids
    assert surface.candidate_graph_node_ids == surface.child_candidate_node_ids
    assert surface.candidate_count == len(surface.candidate_graph_node_ids)
    assert surface.generated_by == "CODE:R_GRAPH_TRAVERSAL_CANDIDATE_SURFACE"
    assert surface.info_class == "absolute"
    assert surface.semantic_judgement_status == "not_run"
    assert any(item["relation"] == "child" for item in surface.candidate_records)


def test_candidate_surface_copies_next_and_previous_candidates_from_next_edges() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    graph_record = record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_149_next_graph_build",
        capsules=[
            _sample_capsule("turn_order_149_next_001"),
            _sample_capsule("turn_order_149_next_002"),
            _sample_capsule("turn_order_149_next_003"),
        ],
        batch_id="batch_order_149_next",
    )
    inspected_node_id = raw_capsule_graph_node_id("turn_order_149_next_002")
    handoff = RLoopMemoryHandoffPacketFrame(
        packet_id="node_0:r_loop_memory_handoff_packet_frame:order_149_next",
        packet_status="available",
        graph_snapshot_id=graph_record.build.snapshot.snapshot_id,
        r_loop_graph_guide_packet_id=graph_record.build.guide_packet.packet_id,
        available_entry_node_ids=[inspected_node_id],
        node_kind_counts=dict(graph_record.build.snapshot.node_kind_counts),
        data_kind_counts=dict(graph_record.build.snapshot.data_kind_counts),
        summary_depth_range=list(graph_record.build.guide_packet.summary_depth_range),
        source_leaf_count_range=list(graph_record.build.guide_packet.source_leaf_count_range),
        source_graph_node_ids=list(graph_record.build.snapshot.source_graph_node_ids),
        source_trace_ids=list(graph_record.build.snapshot.source_trace_ids),
        source_data_ids=[
            graph_record.build.snapshot.snapshot_id,
            graph_record.build.guide_packet.packet_id,
        ],
    )

    result = run_r_loop_dry_run_skeleton(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_149_next_runtime",
        handoff_packet=handoff,
        input_ref=[graph_record.trace_event_id],
        frame_label="order_149_next",
    )

    surface = result.candidate_surface
    previous_node_id = raw_capsule_graph_node_id("turn_order_149_next_001")
    next_node_id = raw_capsule_graph_node_id("turn_order_149_next_003")

    assert surface.child_candidate_node_ids == []
    assert surface.previous_candidate_node_ids == [previous_node_id]
    assert surface.next_candidate_node_ids == [next_node_id]
    assert set(surface.candidate_graph_node_ids) == {previous_node_id, next_node_id}
    assert any(item["relation"] == "previous" for item in surface.candidate_records)
    assert any(item["relation"] == "next" for item in surface.candidate_records)
    assert result.access_ledger.candidate_graph_node_ids[-2:] == [
        next_node_id,
        previous_node_id,
    ]
    assert result.access_ledger.source_data_ids.count(surface.frame_id) == 1


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
