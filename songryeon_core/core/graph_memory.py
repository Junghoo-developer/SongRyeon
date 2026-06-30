from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    CoreEgoTimeAxisFrame,
    GraphMemoryEdgeFrame,
    GraphMemoryNodeFrame,
    GraphMemorySnapshotFrame,
    RLoopGraphGuidePacketFrame,
    TurnStateCapsule,
    validate_core_ego_time_axis_frame,
    validate_graph_memory_edge_frame,
    validate_graph_memory_node_frame,
    validate_graph_memory_snapshot_frame,
    validate_rloop_graph_guide_packet_frame,
)
from songryeon_core.core.trace_store import TraceStore


CORE_EGO_ROOT_NODE_ID = "graph:core_ego:root"
TIME_AXIS_NODE_ID = "graph:axis:time"
TIME_BUNDLE_CHAR_BUDGET_POLICY_ID = "TIME_BUNDLE_CHAR_BUDGET_LEAF_POLICY_V0"
DEFAULT_TIME_BUNDLE_CHAR_BUDGET = 12000


@dataclass
class GraphMemoryBuildResult:
    nodes: list[GraphMemoryNodeFrame]
    edges: list[GraphMemoryEdgeFrame]
    core_ego_time_axis: CoreEgoTimeAxisFrame
    snapshot: GraphMemorySnapshotFrame
    guide_packet: RLoopGraphGuidePacketFrame


@dataclass
class RecordedGraphMemoryResult:
    build: GraphMemoryBuildResult
    trace_event_id: str
    created_data_ids: list[str]
    existing_data_ids: list[str]


@dataclass
class _CapsuleBundle:
    capsules: list[TurnStateCapsule]
    source_char_count: int
    char_budget_status: str


def raw_capsule_graph_node_id(turn_id: str) -> str:
    return f"graph:raw_capsule:{turn_id}"


def time_bundle_graph_node_id(batch_id: str, *, index: int, total: int) -> str:
    if total == 1:
        return f"graph:time_bundle:{batch_id}"
    return f"graph:time_bundle:{batch_id}:{index:03d}"


def graph_memory_snapshot_id(batch_id: str) -> str:
    return f"graph:snapshot:{batch_id}"


def rloop_graph_guide_packet_id(snapshot_id: str) -> str:
    return f"rloop:graph_guide:{snapshot_id}"


def build_graph_memory_snapshot_from_capsules(
    *,
    capsules: list[TurnStateCapsule],
    batch_id: str,
    source_data_ids: list[str] | None = None,
    char_budget: int = DEFAULT_TIME_BUNDLE_CHAR_BUDGET,
) -> GraphMemoryBuildResult:
    """Build a graph-memory snapshot from TurnStateCapsule coordinate fields."""

    if not batch_id:
        raise ValueError("batch_id must not be empty")
    if char_budget <= 0:
        raise ValueError("char_budget must be positive")

    unique_capsules = _dedupe_capsules_by_turn_id(capsules)
    raw_nodes = [_build_raw_capsule_node(capsule) for capsule in unique_capsules]
    for node in raw_nodes:
        validate_graph_memory_node_frame(node)

    raw_nodes_by_turn_id = {
        node.source_turn_id: node
        for node in raw_nodes
        if node.source_turn_id is not None
    }
    bundles = _partition_capsules_by_char_budget(unique_capsules, char_budget=char_budget)
    total_bundles = len(bundles)
    time_bundle_nodes: list[GraphMemoryNodeFrame] = []
    for index, bundle in enumerate(bundles, start=1):
        bundle_raw_nodes = [
            raw_nodes_by_turn_id[capsule.turn_id]
            for capsule in bundle.capsules
            if capsule.turn_id in raw_nodes_by_turn_id
        ]
        node = GraphMemoryNodeFrame(
            node_id=time_bundle_graph_node_id(batch_id, index=index, total=total_bundles),
            node_kind="time_bundle",
            data_kind="time_bundle",
            summary_depth=0,
            source_depth_min=0,
            source_depth_max=0,
            source_leaf_count=len(bundle_raw_nodes),
            source_summary_count=0,
            source_bundle_kind="time_bundle",
            bundle_policy_id=TIME_BUNDLE_CHAR_BUDGET_POLICY_ID,
            char_budget=char_budget,
            source_char_count=bundle.source_char_count,
            char_budget_status=bundle.char_budget_status,
            source_graph_node_ids=[node.node_id for node in bundle_raw_nodes],
            source_trace_ids=_unique_strings(
                [
                    trace_id
                    for raw_node in bundle_raw_nodes
                    for trace_id in raw_node.source_trace_ids
                ]
            ),
            source_data_ids=[],
        )
        validate_graph_memory_node_frame(node)
        time_bundle_nodes.append(node)

    source_leaf_count = len(raw_nodes)
    time_axis_node = GraphMemoryNodeFrame(
        node_id=TIME_AXIS_NODE_ID,
        node_kind="time_axis",
        data_kind="time_axis",
        summary_depth=0,
        source_depth_min=0,
        source_depth_max=0,
        source_leaf_count=source_leaf_count,
        source_summary_count=0,
        source_bundle_kind="time_axis",
        source_graph_node_ids=[node.node_id for node in time_bundle_nodes],
        source_trace_ids=_unique_strings(
            [
                trace_id
                for node in time_bundle_nodes
                for trace_id in node.source_trace_ids
            ]
        ),
    )
    validate_graph_memory_node_frame(time_axis_node)
    core_ego_node = GraphMemoryNodeFrame(
        node_id=CORE_EGO_ROOT_NODE_ID,
        node_kind="core_ego",
        data_kind="core_ego_root",
        summary_depth=0,
        source_depth_min=0,
        source_depth_max=0,
        source_leaf_count=source_leaf_count,
        source_summary_count=0,
        source_bundle_kind="core_ego_time_axis_root",
        source_graph_node_ids=[time_axis_node.node_id],
        source_trace_ids=time_axis_node.source_trace_ids,
    )
    validate_graph_memory_node_frame(core_ego_node)

    nodes = [core_ego_node, time_axis_node, *time_bundle_nodes, *raw_nodes]
    edges = _build_core_ego_time_edges(
        core_ego_node=core_ego_node,
        time_axis_node=time_axis_node,
        time_bundle_nodes=time_bundle_nodes,
    )
    raw_nodes_by_id = {node.node_id: node for node in raw_nodes}
    for bundle_node in time_bundle_nodes:
        for raw_node_id in bundle_node.source_graph_node_ids:
            raw_node = raw_nodes_by_id[raw_node_id]
            edges.append(
                _build_edge(
                    edge_kind="CONTAINS",
                    from_node_id=bundle_node.node_id,
                    to_node_id=raw_node.node_id,
                    source_trace_ids=raw_node.source_trace_ids,
                )
            )
    for edge in edges:
        validate_graph_memory_edge_frame(edge)

    graph_node_ids = [node.node_id for node in nodes]
    graph_edge_ids = [edge.edge_id for edge in edges]
    node_kind_counts = _count_by(nodes, "node_kind")
    edge_kind_counts = _count_by(edges, "edge_kind")
    data_kind_counts = _count_by(nodes, "data_kind")
    source_trace_ids = _unique_strings(
        [trace_id for node in nodes for trace_id in node.source_trace_ids]
    )
    snapshot = GraphMemorySnapshotFrame(
        snapshot_id=graph_memory_snapshot_id(batch_id),
        batch_id=batch_id,
        root_node_id=CORE_EGO_ROOT_NODE_ID,
        time_axis_node_id=TIME_AXIS_NODE_ID,
        graph_node_ids=graph_node_ids,
        graph_edge_ids=graph_edge_ids,
        node_kind_counts=node_kind_counts,
        edge_kind_counts=edge_kind_counts,
        data_kind_counts=data_kind_counts,
        source_graph_node_ids=graph_node_ids,
        source_trace_ids=source_trace_ids,
        source_data_ids=_unique_strings([*graph_node_ids, *graph_edge_ids, *(source_data_ids or [])]),
    )
    validate_graph_memory_snapshot_frame(snapshot)

    core_ego_time_axis = CoreEgoTimeAxisFrame(
        frame_id=f"graph:core_ego_time_axis:{batch_id}",
        batch_id=batch_id,
        core_ego_node_id=CORE_EGO_ROOT_NODE_ID,
        time_axis_node_id=TIME_AXIS_NODE_ID,
        time_bundle_node_ids=[node.node_id for node in time_bundle_nodes],
        raw_capsule_node_ids=[node.node_id for node in raw_nodes],
        edge_ids=graph_edge_ids,
        source_graph_node_ids=graph_node_ids,
        source_trace_ids=source_trace_ids,
        source_data_ids=[snapshot.snapshot_id],
    )
    validate_core_ego_time_axis_frame(core_ego_time_axis)

    guide_packet = _build_rloop_guide_packet(
        snapshot=snapshot,
        nodes=nodes,
        source_data_ids=[snapshot.snapshot_id, *graph_node_ids, *graph_edge_ids],
    )
    validate_rloop_graph_guide_packet_frame(guide_packet)

    return GraphMemoryBuildResult(
        nodes=nodes,
        edges=edges,
        core_ego_time_axis=core_ego_time_axis,
        snapshot=snapshot,
        guide_packet=guide_packet,
    )


def record_graph_memory_for_capsules(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    capsules: list[TurnStateCapsule],
    batch_id: str,
    source_data_ids: list[str] | None = None,
    char_budget: int = DEFAULT_TIME_BUNDLE_CHAR_BUDGET,
) -> RecordedGraphMemoryResult:
    """Record graph-memory node, edge, snapshot, and R loop guide frames in DataStore."""

    build = build_graph_memory_snapshot_from_capsules(
        capsules=capsules,
        batch_id=batch_id,
        source_data_ids=source_data_ids,
        char_budget=char_budget,
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="graph_memory_builder",
        event_type="node_output",
        input_ref=build.snapshot.source_trace_ids,
        output_ref=[build.snapshot.snapshot_id, build.guide_packet.packet_id],
        schema_status="passed",
    )

    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    for node in build.nodes:
        _record_payload_if_missing(
            data_store=data_store,
            data_id=node.node_id,
            data_type=f"graph_memory:node:{node.node_kind}",
            payload=asdict(node),
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            created_data_ids=created_data_ids,
            existing_data_ids=existing_data_ids,
        )
    for edge in build.edges:
        _record_payload_if_missing(
            data_store=data_store,
            data_id=edge.edge_id,
            data_type=f"graph_memory:edge:{edge.edge_kind}",
            payload=asdict(edge),
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            created_data_ids=created_data_ids,
            existing_data_ids=existing_data_ids,
        )
    _record_payload_if_missing(
        data_store=data_store,
        data_id=build.core_ego_time_axis.frame_id,
        data_type="graph_memory:core_ego_time_axis_frame",
        payload=asdict(build.core_ego_time_axis),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    _record_payload_if_missing(
        data_store=data_store,
        data_id=build.snapshot.snapshot_id,
        data_type="graph_memory:snapshot",
        payload=asdict(build.snapshot),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    _record_payload_if_missing(
        data_store=data_store,
        data_id=build.guide_packet.packet_id,
        data_type="graph_memory:rloop_guide_packet",
        payload=asdict(build.guide_packet),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )

    return RecordedGraphMemoryResult(
        build=build,
        trace_event_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def _build_raw_capsule_node(capsule: TurnStateCapsule) -> GraphMemoryNodeFrame:
    if not capsule.turn_id:
        raise ValueError("TurnStateCapsule.turn_id must not be empty")
    source_trace_ids = _unique_strings(capsule.trace_event_ids)
    user_input_trace_id = (
        capsule.user_input_trace_id
        if capsule.user_input_trace_id in source_trace_ids
        else None
    )
    final_response_trace_id = (
        capsule.final_response_trace_id
        if capsule.final_response_trace_id in source_trace_ids
        else None
    )
    return GraphMemoryNodeFrame(
        node_id=raw_capsule_graph_node_id(capsule.turn_id),
        node_kind="raw_capsule",
        data_kind="turn_state_capsule",
        source_turn_id=capsule.turn_id,
        trace_count=len(capsule.trace_event_ids),
        movement_count=len(capsule.node_movements),
        user_input_trace_id=user_input_trace_id,
        final_response_trace_id=final_response_trace_id,
        summary_depth=0,
        source_depth_min=0,
        source_depth_max=0,
        source_leaf_count=1,
        source_summary_count=0,
        source_bundle_kind="raw_leaf",
        source_char_count=_capsule_coordinate_char_count(capsule),
        source_graph_node_ids=[],
        source_trace_ids=source_trace_ids,
        source_data_ids=[],
    )


def _partition_capsules_by_char_budget(
    capsules: list[TurnStateCapsule],
    *,
    char_budget: int,
) -> list[_CapsuleBundle]:
    if not capsules:
        return [_CapsuleBundle(capsules=[], source_char_count=0, char_budget_status="within_budget")]

    bundles: list[_CapsuleBundle] = []
    current: list[TurnStateCapsule] = []
    current_chars = 0
    current_status = "within_budget"
    for capsule in capsules:
        capsule_chars = _capsule_coordinate_char_count(capsule)
        if current and current_chars + capsule_chars > char_budget:
            bundles.append(
                _CapsuleBundle(
                    capsules=current,
                    source_char_count=current_chars,
                    char_budget_status=current_status,
                )
            )
            current = []
            current_chars = 0
            current_status = "within_budget"
        if not current and capsule_chars > char_budget:
            bundles.append(
                _CapsuleBundle(
                    capsules=[capsule],
                    source_char_count=capsule_chars,
                    char_budget_status="leaf_exceeds_budget_kept_whole",
                )
            )
            continue
        current.append(capsule)
        current_chars += capsule_chars
    if current:
        bundles.append(
            _CapsuleBundle(
                capsules=current,
                source_char_count=current_chars,
                char_budget_status=current_status,
            )
        )
    return bundles


def _build_core_ego_time_edges(
    *,
    core_ego_node: GraphMemoryNodeFrame,
    time_axis_node: GraphMemoryNodeFrame,
    time_bundle_nodes: list[GraphMemoryNodeFrame],
) -> list[GraphMemoryEdgeFrame]:
    edges = [
        _build_edge(
            edge_kind="CONTAINS",
            from_node_id=core_ego_node.node_id,
            to_node_id=time_axis_node.node_id,
            source_trace_ids=time_axis_node.source_trace_ids,
        )
    ]
    for bundle_node in time_bundle_nodes:
        edges.append(
            _build_edge(
                edge_kind="CHILD_OF_TIME_AXIS",
                from_node_id=time_axis_node.node_id,
                to_node_id=bundle_node.node_id,
                source_trace_ids=bundle_node.source_trace_ids,
            )
        )
    return edges


def _build_edge(
    *,
    edge_kind: str,
    from_node_id: str,
    to_node_id: str,
    source_trace_ids: list[str],
) -> GraphMemoryEdgeFrame:
    return GraphMemoryEdgeFrame(
        edge_id=f"graph:edge:{edge_kind.lower()}:{from_node_id}:{to_node_id}",
        edge_kind=edge_kind,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        source_graph_node_ids=[from_node_id, to_node_id],
        source_trace_ids=source_trace_ids,
        source_data_ids=[from_node_id, to_node_id],
    )


def _build_rloop_guide_packet(
    *,
    snapshot: GraphMemorySnapshotFrame,
    nodes: list[GraphMemoryNodeFrame],
    source_data_ids: list[str],
) -> RLoopGraphGuidePacketFrame:
    summary_depths = [node.summary_depth for node in nodes]
    source_leaf_counts = [node.source_leaf_count for node in nodes]
    risky_or_unreviewed_node_ids = [
        node.node_id
        for node in nodes
        if node.node_kind == "summary" or node.semantic_judgement_status != "not_run"
    ]
    return RLoopGraphGuidePacketFrame(
        packet_id=rloop_graph_guide_packet_id(snapshot.snapshot_id),
        graph_snapshot_id=snapshot.snapshot_id,
        target_consumer="R_LOOP",
        available_entry_nodes=[snapshot.time_axis_node_id],
        node_kind_counts=dict(snapshot.node_kind_counts),
        data_kind_counts=dict(snapshot.data_kind_counts),
        summary_depth_range=_int_range(summary_depths),
        source_leaf_count_range=_int_range(source_leaf_counts),
        risky_or_unreviewed_node_ids=risky_or_unreviewed_node_ids,
        recommended_traversal_hints=[],
        recommended_traversal_hints_status="not_run",
        source_graph_node_ids=list(snapshot.graph_node_ids),
        source_trace_ids=list(snapshot.source_trace_ids),
        source_data_ids=_unique_strings(source_data_ids),
        generated_by="CODE:GRAPH_MEMORY_GUIDE_BUILDER",
        info_class="absolute",
        semantic_judgement_status="not_run",
    )


def _record_payload_if_missing(
    *,
    data_store: DataStore,
    data_id: str,
    data_type: str,
    payload: dict[str, object],
    created_at: str,
    source_trace_id: str,
    created_data_ids: list[str],
    existing_data_ids: list[str],
) -> None:
    existing = data_store.get_record(data_id)
    if existing is not None:
        if existing.data_type != data_type:
            raise ValueError(f"graph memory data_id collision with different type: {data_id}")
        if existing.payload != payload:
            raise ValueError(f"graph memory data_id collision with different payload: {data_id}")
        existing_data_ids.append(data_id)
        return
    data_store.create_record(
        data_id=data_id,
        data_type=data_type,
        exists=True,
        created_at=created_at,
        source_trace_id=source_trace_id,
        payload=payload,
    )
    created_data_ids.append(data_id)


def _dedupe_capsules_by_turn_id(capsules: list[TurnStateCapsule]) -> list[TurnStateCapsule]:
    seen: set[str] = set()
    unique_capsules: list[TurnStateCapsule] = []
    for capsule in capsules:
        if not capsule.turn_id:
            raise ValueError("TurnStateCapsule.turn_id must not be empty")
        if capsule.turn_id in seen:
            continue
        seen.add(capsule.turn_id)
        unique_capsules.append(capsule)
    return unique_capsules


def _capsule_coordinate_char_count(capsule: TurnStateCapsule) -> int:
    return len(json.dumps(asdict(capsule), ensure_ascii=False, sort_keys=True))


def _count_by(items: list[object], attr_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = getattr(item, attr_name)
        if not isinstance(value, str):
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def _int_range(values: list[int]) -> list[int]:
    if not values:
        return [0, 0]
    return [min(values), max(values)]


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
