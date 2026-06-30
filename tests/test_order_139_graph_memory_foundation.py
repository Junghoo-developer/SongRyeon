from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import (
    CORE_EGO_ROOT_NODE_ID,
    TIME_AXIS_NODE_ID,
    build_graph_memory_snapshot_from_capsules,
    raw_capsule_graph_node_id,
    record_graph_memory_for_capsules,
)
from songryeon_core.core.schemas import NodeMovement, TurnStateCapsule
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.runtime.dry_run import run_dry_turn


def test_duplicate_capsule_ingest_creates_one_raw_graph_node() -> None:
    capsule = _sample_capsule()

    build = build_graph_memory_snapshot_from_capsules(
        capsules=[capsule, capsule],
        batch_id="batch_order_139",
    )

    raw_nodes = [node for node in build.nodes if node.node_kind == "raw_capsule"]
    assert len(raw_nodes) == 1
    assert raw_nodes[0].node_id == raw_capsule_graph_node_id(capsule.turn_id)

    trace_store = TraceStore()
    data_store = DataStore()
    first = record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_139",
        capsules=[capsule, capsule],
        batch_id="batch_order_139",
    )
    second = record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_139",
        capsules=[capsule, capsule],
        batch_id="batch_order_139",
    )

    raw_records = [
        record
        for record in data_store.list_records()
        if record.data_type == "graph_memory:node:raw_capsule"
    ]
    assert len(raw_records) == 1
    assert first.created_data_ids
    assert not second.created_data_ids
    assert raw_records[0].data_id == raw_capsule_graph_node_id(capsule.turn_id)


def test_raw_capsule_node_contains_absolute_coordinates_only() -> None:
    capsule = _sample_capsule()

    build = build_graph_memory_snapshot_from_capsules(
        capsules=[capsule],
        batch_id="batch_order_139",
    )
    raw_node = next(node for node in build.nodes if node.node_kind == "raw_capsule")
    payload = asdict(raw_node)

    assert payload["source_turn_id"] == capsule.turn_id
    assert payload["trace_count"] == len(capsule.trace_event_ids)
    assert payload["movement_count"] == len(capsule.node_movements)
    assert payload["user_input_trace_id"] == capsule.user_input_trace_id
    assert payload["final_response_trace_id"] == capsule.final_response_trace_id
    assert payload["generated_by"] == "CODE:GRAPH_MEMORY_BUILDER"
    assert payload["info_class"] == "absolute"
    assert payload["semantic_judgement_status"] == "not_run"
    for forbidden_field in (
        "memory_text",
        "summary_text",
        "raw_user_text",
        "raw_assistant_text",
        "semantic_topic",
        "topic_label",
        "importance_reason",
        "relevance_reason",
    ):
        assert forbidden_field not in payload


def test_core_ego_time_axis_edges_are_created_without_semantic_axis() -> None:
    capsule = _sample_capsule()

    build = build_graph_memory_snapshot_from_capsules(
        capsules=[capsule],
        batch_id="batch_order_139",
    )

    edge_tuples = {
        (edge.edge_kind, edge.from_node_id, edge.to_node_id)
        for edge in build.edges
    }
    bundle_node = next(node for node in build.nodes if node.node_kind == "time_bundle")
    raw_node_id = raw_capsule_graph_node_id(capsule.turn_id)

    assert ("CONTAINS", CORE_EGO_ROOT_NODE_ID, TIME_AXIS_NODE_ID) in edge_tuples
    assert ("CHILD_OF_TIME_AXIS", TIME_AXIS_NODE_ID, bundle_node.node_id) in edge_tuples
    assert ("CONTAINS", bundle_node.node_id, raw_node_id) in edge_tuples
    assert all(node.node_kind != "semantic_topic" for node in build.nodes)
    assert build.core_ego_time_axis.semantic_axis_status == "not_created"


def test_raw_capsule_summary_depth_and_source_counts_are_zero_depth_leaf() -> None:
    build = build_graph_memory_snapshot_from_capsules(
        capsules=[_sample_capsule()],
        batch_id="batch_order_139",
    )
    raw_node = next(node for node in build.nodes if node.node_kind == "raw_capsule")

    assert raw_node.summary_depth == 0
    assert raw_node.source_depth_min == 0
    assert raw_node.source_depth_max == 0
    assert raw_node.source_leaf_count == 1
    assert raw_node.source_summary_count == 0
    assert raw_node.source_bundle_kind == "raw_leaf"


def test_rloop_graph_guide_packet_records_counts_ranges_and_sources() -> None:
    capsule = _sample_capsule()

    build = build_graph_memory_snapshot_from_capsules(
        capsules=[capsule],
        batch_id="batch_order_139",
    )
    guide = build.guide_packet
    raw_node_id = raw_capsule_graph_node_id(capsule.turn_id)

    assert guide.graph_snapshot_id == build.snapshot.snapshot_id
    assert guide.target_consumer == "R_LOOP"
    assert guide.available_entry_nodes == [TIME_AXIS_NODE_ID]
    assert guide.node_kind_counts["raw_capsule"] == 1
    assert guide.node_kind_counts["time_bundle"] == 1
    assert guide.data_kind_counts["turn_state_capsule"] == 1
    assert guide.summary_depth_range == [0, 0]
    assert guide.source_leaf_count_range == [1, 1]
    assert raw_node_id in guide.source_graph_node_ids
    assert build.snapshot.snapshot_id in guide.source_data_ids
    assert set(capsule.trace_event_ids).issubset(set(guide.source_trace_ids))
    assert guide.risky_or_unreviewed_node_ids == []
    assert guide.generated_by == "CODE:GRAPH_MEMORY_GUIDE_BUILDER"
    assert guide.info_class == "absolute"
    assert guide.semantic_judgement_status == "not_run"
    assert guide.recommended_traversal_hints_status == "not_run"
    assert guide.recommended_traversal_hints == []


def test_runtime_graph_guide_is_not_injected_into_node1_or_node3() -> None:
    result = run_dry_turn()
    guide_id = result["rloop_graph_guide_packet_id"]

    assert result["rloop_graph_guide_hints_status"] == "not_run"
    assert result["rloop_graph_guide_semantic_judgement_status"] == "not_run"
    assert result["graph_memory_raw_capsule_node_count"] >= 1

    guide_records = [
        record
        for record in result["data_records"]
        if record["data_type"] == "graph_memory:rloop_guide_packet"
    ]
    assert len(guide_records) == 1
    assert guide_records[0]["data_id"] == guide_id

    for record in result["data_records"]:
        if record["data_type"] not in {"node_output:routing_decision", "node_output:report"}:
            continue
        source_data_ids = record["payload"].get("source_data_ids", [])
        assert guide_id not in source_data_ids


def _sample_capsule(turn_id: str = "turn_order_139_previous") -> TurnStateCapsule:
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
