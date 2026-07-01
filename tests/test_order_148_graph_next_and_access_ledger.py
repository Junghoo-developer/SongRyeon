from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import (
    TIME_AXIS_NODE_ID,
    build_graph_memory_snapshot_from_capsules,
    raw_capsule_graph_node_id,
    record_graph_memory_for_capsules,
)
from songryeon_core.core.schemas import NodeMovement, TurnStateCapsule
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.r_loop_dry_run import run_r_loop_dry_run_skeleton
from songryeon_core.nodes.node_0_memory_supplier import record_r_loop_memory_handoff_packet


def test_raw_capsule_next_edges_follow_deduped_capsule_order() -> None:
    capsules = [
        _sample_capsule("turn_order_148_001"),
        _sample_capsule("turn_order_148_002"),
        _sample_capsule("turn_order_148_002"),
        _sample_capsule("turn_order_148_003"),
    ]

    build = build_graph_memory_snapshot_from_capsules(
        capsules=capsules,
        batch_id="batch_order_148",
    )

    next_edges = [edge for edge in build.edges if edge.edge_kind == "NEXT"]
    next_pairs = [(edge.from_node_id, edge.to_node_id) for edge in next_edges]

    assert next_pairs == [
        (
            raw_capsule_graph_node_id("turn_order_148_001"),
            raw_capsule_graph_node_id("turn_order_148_002"),
        ),
        (
            raw_capsule_graph_node_id("turn_order_148_002"),
            raw_capsule_graph_node_id("turn_order_148_003"),
        ),
    ]
    assert build.snapshot.edge_kind_counts["NEXT"] == 2
    assert all(edge.info_class == "absolute" for edge in next_edges)
    assert all(edge.semantic_judgement_status == "not_run" for edge in next_edges)


def test_r_dry_run_records_turn_graph_access_ledger_without_semantic_judgement() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    graph_record = record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_148_graph_build",
        capsules=[
            _sample_capsule("turn_order_148_previous_001"),
            _sample_capsule("turn_order_148_previous_002"),
        ],
        batch_id="batch_order_148_access",
    )
    handoff_trace_id, handoff_data_id, handoff = record_r_loop_memory_handoff_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_148_runtime",
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
        turn_id="turn_order_148_runtime",
        handoff_packet=handoff,
        input_ref=[handoff_trace_id],
        frame_label="order_148",
    )

    ledger = result.access_ledger
    ledger_record = data_store.require_record(ledger.frame_id)

    assert ledger_record.data_type == "graph_memory:turn_access_ledger_frame"
    assert ledger.frame_id in result.output_data_ids
    assert ledger.turn_id == "turn_order_148_runtime"
    assert ledger.turn_capsule_graph_node_id == raw_capsule_graph_node_id(
        "turn_order_148_runtime"
    )
    assert ledger.candidate_graph_node_ids[0] == TIME_AXIS_NODE_ID
    assert ledger.selected_graph_node_ids == [
        TIME_AXIS_NODE_ID,
        "graph:time_bundle:batch_order_148_access",
        raw_capsule_graph_node_id("turn_order_148_previous_001"),
    ]
    assert ledger.inspected_graph_node_ids == ledger.selected_graph_node_ids
    assert ledger.read_graph_node_ids == []
    assert ledger.used_as_answer_source_graph_node_ids == []
    assert ledger.generated_by == "CODE:GRAPH_ACCESS_LEDGER"
    assert ledger.info_class == "absolute"
    assert ledger.semantic_judgement_status == "not_run"
    assert handoff_data_id in ledger.source_data_ids
    assert any(record["stage"] == "selected" for record in ledger.access_records)
    assert any(record["stage"] == "inspected" for record in ledger.access_records)
    assert "relevance_reason" not in ledger_record.payload
    assert "importance_reason" not in ledger_record.payload


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
