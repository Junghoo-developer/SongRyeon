from __future__ import annotations

from dataclasses import asdict, replace

import pytest

from songryeon_core.core.graph_memory import (
    CORE_EGO_ROOT_NODE_ID,
    TIME_AXIS_NODE_ID,
    build_graph_memory_snapshot_from_capsules,
)
from songryeon_core.core.graph_memory_store import (
    SONGRYEON_GRAPH_NAMESPACE,
    SONGRYEON_VESSEL_DATABASE_NAME,
    SONGRYEON_VESSEL_SERVICE_NAME,
    InMemoryGraphMemoryStore,
)
from songryeon_core.core.schemas import NodeMovement, TurnStateCapsule


def test_in_memory_store_upserts_and_reads_graph_nodes_and_edges() -> None:
    build = build_graph_memory_snapshot_from_capsules(
        capsules=[_sample_capsule()],
        batch_id="batch_order_142",
    )
    store = InMemoryGraphMemoryStore()

    for node in build.nodes:
        store.upsert_node(node)
    for edge in build.edges:
        store.upsert_edge(edge)

    assert store.node_count() == len(build.nodes)
    assert store.edge_count() == len(build.edges)
    assert store.get_node(CORE_EGO_ROOT_NODE_ID).node_id == CORE_EGO_ROOT_NODE_ID

    core_children = store.list_children(CORE_EGO_ROOT_NODE_ID)
    assert [node.node_id for node in core_children] == [TIME_AXIS_NODE_ID]

    time_entries = store.list_core_ego_entries(axis="time")
    assert [node.node_id for node in time_entries] == [TIME_AXIS_NODE_ID]
    assert store.list_core_ego_entries(axis="semantic") == []


def test_in_memory_store_upsert_is_idempotent_for_same_payload() -> None:
    build = build_graph_memory_snapshot_from_capsules(
        capsules=[_sample_capsule()],
        batch_id="batch_order_142",
    )
    store = InMemoryGraphMemoryStore()
    node = build.nodes[0]
    edge = build.edges[0]

    store.upsert_node(node)
    store.upsert_node(node)
    for required_node_id in {edge.from_node_id, edge.to_node_id}:
        required_node = next(item for item in build.nodes if item.node_id == required_node_id)
        store.upsert_node(required_node)
    store.upsert_edge(edge)
    store.upsert_edge(edge)

    assert store.node_count() == len({node.node_id, edge.from_node_id, edge.to_node_id})
    assert store.edge_count() == 1


def test_in_memory_store_rejects_same_id_with_different_payload() -> None:
    build = build_graph_memory_snapshot_from_capsules(
        capsules=[_sample_capsule()],
        batch_id="batch_order_142",
    )
    store = InMemoryGraphMemoryStore()
    node = next(item for item in build.nodes if item.node_kind == "raw_capsule")

    store.upsert_node(node)
    changed = replace(node, trace_count=node.trace_count + 1)

    with pytest.raises(ValueError, match="different payload"):
        store.upsert_node(changed)


def test_graph_memory_store_preserves_source_provenance_round_trip() -> None:
    capsule = _sample_capsule()
    build = build_graph_memory_snapshot_from_capsules(
        capsules=[capsule],
        batch_id="batch_order_142",
    )
    store = InMemoryGraphMemoryStore()
    raw_node = next(node for node in build.nodes if node.node_kind == "raw_capsule")

    store.upsert_node(raw_node)
    retrieved = store.get_node(raw_node.node_id)

    assert retrieved is not None
    assert retrieved.source_trace_ids == raw_node.source_trace_ids
    assert retrieved.source_data_ids == raw_node.source_data_ids
    assert retrieved.source_graph_node_ids == raw_node.source_graph_node_ids
    assert set(capsule.trace_event_ids).issubset(set(retrieved.source_trace_ids))


def test_graph_memory_store_snapshot_round_trips_counts_without_external_db() -> None:
    build = build_graph_memory_snapshot_from_capsules(
        capsules=[_sample_capsule()],
        batch_id="batch_order_142",
    )
    store = InMemoryGraphMemoryStore()
    for node in build.nodes:
        store.upsert_node(node)
    for edge in build.edges:
        store.upsert_edge(edge)

    snapshot = store.snapshot(
        snapshot_id="graph:snapshot:store_boundary",
        batch_id="batch_order_142",
    )

    assert snapshot.node_kind_counts["raw_capsule"] == 1
    assert snapshot.node_kind_counts["core_ego"] == 1
    assert snapshot.edge_kind_counts["CONTAINS"] >= 1
    assert snapshot.root_node_id == CORE_EGO_ROOT_NODE_ID
    assert snapshot.time_axis_node_id == TIME_AXIS_NODE_ID


def test_graph_memory_store_does_not_generate_semantic_topic_fields() -> None:
    build = build_graph_memory_snapshot_from_capsules(
        capsules=[_sample_capsule()],
        batch_id="batch_order_142",
    )
    store = InMemoryGraphMemoryStore()
    raw_node = next(node for node in build.nodes if node.node_kind == "raw_capsule")

    store.upsert_node(raw_node)
    payload = asdict(store.get_node(raw_node.node_id))

    assert payload["generated_by"] == "CODE:GRAPH_MEMORY_BUILDER"
    assert payload["info_class"] == "absolute"
    assert payload["semantic_judgement_status"] == "not_run"
    for forbidden_field in (
        "semantic_topic",
        "topic_label",
        "topic_assignment_generated_by",
        "meaning_cluster",
        "embedding_id",
    ):
        assert forbidden_field not in payload


def test_songryeon_vessel_names_are_reserved_without_connecting_external_db() -> None:
    assert SONGRYEON_VESSEL_SERVICE_NAME == "songryeon-neo4j-vessel"
    assert SONGRYEON_VESSEL_DATABASE_NAME == "songryeon_vessel"
    assert SONGRYEON_GRAPH_NAMESPACE == "songryeon_core_graph_v0"


def _sample_capsule(turn_id: str = "turn_order_142") -> TurnStateCapsule:
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
