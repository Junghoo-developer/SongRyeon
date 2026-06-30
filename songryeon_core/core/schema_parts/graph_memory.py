from __future__ import annotations

from dataclasses import dataclass, field

from songryeon_core.core.schema_parts.base import (
    _validate_no_duplicates,
    _validate_string_list,
)


GRAPH_MEMORY_NODE_FRAME_SCHEMA_NAME = "GraphMemoryNodeFrame"
GRAPH_MEMORY_NODE_FRAME_SCHEMA_VERSION = "0.1"
GRAPH_MEMORY_EDGE_FRAME_SCHEMA_NAME = "GraphMemoryEdgeFrame"
GRAPH_MEMORY_EDGE_FRAME_SCHEMA_VERSION = "0.1"
GRAPH_MEMORY_SNAPSHOT_FRAME_SCHEMA_NAME = "GraphMemorySnapshotFrame"
GRAPH_MEMORY_SNAPSHOT_FRAME_SCHEMA_VERSION = "0.1"
CORE_EGO_TIME_AXIS_FRAME_SCHEMA_NAME = "CoreEgoTimeAxisFrame"
CORE_EGO_TIME_AXIS_FRAME_SCHEMA_VERSION = "0.1"
RLOOP_GRAPH_GUIDE_PACKET_FRAME_SCHEMA_NAME = "RLoopGraphGuidePacketFrame"
RLOOP_GRAPH_GUIDE_PACKET_FRAME_SCHEMA_VERSION = "0.1"

GRAPH_MEMORY_NODE_KINDS = {
    "raw_capsule",
    "raw_bundle",
    "summary",
    "core_ego",
    "time_axis",
    "time_bundle",
}
GRAPH_MEMORY_EDGE_KINDS = {
    "CONTAINS",
    "CHILD_OF_TIME_AXIS",
    "SOURCE_OF",
    "SUMMARY_OF",
}
GRAPH_MEMORY_CODE_GENERATOR = "CODE:GRAPH_MEMORY_BUILDER"
RLOOP_GUIDE_CODE_GENERATOR = "CODE:GRAPH_MEMORY_GUIDE_BUILDER"


@dataclass
class GraphMemoryNodeFrame:
    """A graph-memory node that keeps source coordinates, not semantic memory text."""

    node_id: str
    node_kind: str
    data_kind: str
    source_turn_id: str | None = None
    trace_count: int = 0
    movement_count: int = 0
    user_input_trace_id: str | None = None
    final_response_trace_id: str | None = None
    summary_depth: int = 0
    source_depth_min: int = 0
    source_depth_max: int = 0
    source_leaf_count: int = 0
    source_summary_count: int = 0
    source_bundle_kind: str = "none"
    bundle_policy_id: str = "not_applicable"
    char_budget: int | None = None
    source_char_count: int = 0
    char_budget_status: str = "not_applicable"
    source_graph_node_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = GRAPH_MEMORY_CODE_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = GRAPH_MEMORY_NODE_FRAME_SCHEMA_NAME
    schema_version: str = GRAPH_MEMORY_NODE_FRAME_SCHEMA_VERSION


@dataclass
class GraphMemoryEdgeFrame:
    """A graph-memory edge with deterministic source and target node coordinates."""

    edge_id: str
    edge_kind: str
    from_node_id: str
    to_node_id: str
    source_graph_node_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = GRAPH_MEMORY_CODE_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = GRAPH_MEMORY_EDGE_FRAME_SCHEMA_NAME
    schema_version: str = GRAPH_MEMORY_EDGE_FRAME_SCHEMA_VERSION


@dataclass
class GraphMemorySnapshotFrame:
    """The code-checkable graph-memory node and edge set for one batch."""

    snapshot_id: str
    batch_id: str
    root_node_id: str
    time_axis_node_id: str
    graph_node_ids: list[str] = field(default_factory=list)
    graph_edge_ids: list[str] = field(default_factory=list)
    node_kind_counts: dict[str, int] = field(default_factory=dict)
    edge_kind_counts: dict[str, int] = field(default_factory=dict)
    data_kind_counts: dict[str, int] = field(default_factory=dict)
    source_graph_node_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = GRAPH_MEMORY_CODE_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = GRAPH_MEMORY_SNAPSHOT_FRAME_SCHEMA_NAME
    schema_version: str = GRAPH_MEMORY_SNAPSHOT_FRAME_SCHEMA_VERSION


@dataclass
class CoreEgoTimeAxisFrame:
    """The first CoreEgo graph entry surface: root to time axis only."""

    frame_id: str
    batch_id: str
    core_ego_node_id: str
    time_axis_node_id: str
    time_bundle_node_ids: list[str] = field(default_factory=list)
    raw_capsule_node_ids: list[str] = field(default_factory=list)
    edge_ids: list[str] = field(default_factory=list)
    source_graph_node_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = GRAPH_MEMORY_CODE_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    semantic_axis_status: str = "not_created"
    schema_name: str = CORE_EGO_TIME_AXIS_FRAME_SCHEMA_NAME
    schema_version: str = CORE_EGO_TIME_AXIS_FRAME_SCHEMA_VERSION


@dataclass
class RLoopGraphGuidePacketFrame:
    """A code-generated guide packet for a future R loop graph traversal."""

    packet_id: str
    graph_snapshot_id: str
    target_consumer: str = "R_LOOP"
    available_entry_nodes: list[str] = field(default_factory=list)
    node_kind_counts: dict[str, int] = field(default_factory=dict)
    data_kind_counts: dict[str, int] = field(default_factory=dict)
    summary_depth_range: list[int] = field(default_factory=lambda: [0, 0])
    source_leaf_count_range: list[int] = field(default_factory=lambda: [0, 0])
    risky_or_unreviewed_node_ids: list[str] = field(default_factory=list)
    recommended_traversal_hints: list[str] = field(default_factory=list)
    recommended_traversal_hints_status: str = "not_run"
    source_graph_node_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = RLOOP_GUIDE_CODE_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = RLOOP_GRAPH_GUIDE_PACKET_FRAME_SCHEMA_NAME
    schema_version: str = RLOOP_GRAPH_GUIDE_PACKET_FRAME_SCHEMA_VERSION


def validate_graph_memory_node_frame(frame: GraphMemoryNodeFrame) -> None:
    _require_text_fields(
        "GraphMemoryNodeFrame",
        {
            "node_id": frame.node_id,
            "node_kind": frame.node_kind,
            "data_kind": frame.data_kind,
            "source_bundle_kind": frame.source_bundle_kind,
            "bundle_policy_id": frame.bundle_policy_id,
            "char_budget_status": frame.char_budget_status,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.schema_name != GRAPH_MEMORY_NODE_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown graph memory node schema_name: {frame.schema_name}")
    if frame.schema_version != GRAPH_MEMORY_NODE_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown graph memory node schema_version: {frame.schema_version}")
    if frame.node_kind not in GRAPH_MEMORY_NODE_KINDS:
        raise ValueError(f"unknown graph memory node_kind: {frame.node_kind}")
    if frame.generated_by != GRAPH_MEMORY_CODE_GENERATOR:
        raise ValueError("GraphMemoryNodeFrame.generated_by must be code builder")
    if frame.info_class != "absolute":
        raise ValueError("GraphMemoryNodeFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("GraphMemoryNodeFrame.semantic_judgement_status must be not_run")

    _validate_non_negative_ints(
        "GraphMemoryNodeFrame",
        {
            "trace_count": frame.trace_count,
            "movement_count": frame.movement_count,
            "summary_depth": frame.summary_depth,
            "source_depth_min": frame.source_depth_min,
            "source_depth_max": frame.source_depth_max,
            "source_leaf_count": frame.source_leaf_count,
            "source_summary_count": frame.source_summary_count,
            "source_char_count": frame.source_char_count,
        },
    )
    if frame.char_budget is not None and frame.char_budget <= 0:
        raise ValueError("GraphMemoryNodeFrame.char_budget must be positive when set")
    if frame.source_depth_min > frame.source_depth_max:
        raise ValueError("GraphMemoryNodeFrame source depth range is inverted")

    _validate_string_list("GraphMemoryNodeFrame.source_graph_node_ids", frame.source_graph_node_ids)
    _validate_string_list("GraphMemoryNodeFrame.source_trace_ids", frame.source_trace_ids)
    _validate_string_list("GraphMemoryNodeFrame.source_data_ids", frame.source_data_ids)
    _validate_no_duplicates(
        "GraphMemoryNodeFrame.source_graph_node_ids",
        frame.source_graph_node_ids,
    )
    _validate_no_duplicates("GraphMemoryNodeFrame.source_trace_ids", frame.source_trace_ids)
    _validate_no_duplicates("GraphMemoryNodeFrame.source_data_ids", frame.source_data_ids)

    if frame.user_input_trace_id is not None and frame.user_input_trace_id not in frame.source_trace_ids:
        raise ValueError("raw user trace anchor must be present in source_trace_ids")
    if frame.final_response_trace_id is not None and frame.final_response_trace_id not in frame.source_trace_ids:
        raise ValueError("raw final trace anchor must be present in source_trace_ids")

    if frame.node_kind == "raw_capsule":
        if not frame.source_turn_id:
            raise ValueError("raw capsule graph node must include source_turn_id")
        if frame.summary_depth != 0:
            raise ValueError("raw capsule summary_depth must be 0")
        if frame.source_leaf_count != 1:
            raise ValueError("raw capsule source_leaf_count must be 1")
        if frame.source_summary_count != 0:
            raise ValueError("raw capsule source_summary_count must be 0")


def validate_graph_memory_edge_frame(frame: GraphMemoryEdgeFrame) -> None:
    _require_text_fields(
        "GraphMemoryEdgeFrame",
        {
            "edge_id": frame.edge_id,
            "edge_kind": frame.edge_kind,
            "from_node_id": frame.from_node_id,
            "to_node_id": frame.to_node_id,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.schema_name != GRAPH_MEMORY_EDGE_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown graph memory edge schema_name: {frame.schema_name}")
    if frame.schema_version != GRAPH_MEMORY_EDGE_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown graph memory edge schema_version: {frame.schema_version}")
    if frame.edge_kind not in GRAPH_MEMORY_EDGE_KINDS:
        raise ValueError(f"unknown graph memory edge_kind: {frame.edge_kind}")
    if frame.from_node_id == frame.to_node_id:
        raise ValueError("GraphMemoryEdgeFrame must not be a self edge")
    if frame.generated_by != GRAPH_MEMORY_CODE_GENERATOR:
        raise ValueError("GraphMemoryEdgeFrame.generated_by must be code builder")
    if frame.info_class != "absolute":
        raise ValueError("GraphMemoryEdgeFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("GraphMemoryEdgeFrame.semantic_judgement_status must be not_run")
    _validate_string_list("GraphMemoryEdgeFrame.source_graph_node_ids", frame.source_graph_node_ids)
    _validate_string_list("GraphMemoryEdgeFrame.source_trace_ids", frame.source_trace_ids)
    _validate_string_list("GraphMemoryEdgeFrame.source_data_ids", frame.source_data_ids)
    _validate_no_duplicates(
        "GraphMemoryEdgeFrame.source_graph_node_ids",
        frame.source_graph_node_ids,
    )
    _validate_no_duplicates("GraphMemoryEdgeFrame.source_trace_ids", frame.source_trace_ids)
    _validate_no_duplicates("GraphMemoryEdgeFrame.source_data_ids", frame.source_data_ids)


def validate_graph_memory_snapshot_frame(frame: GraphMemorySnapshotFrame) -> None:
    _require_text_fields(
        "GraphMemorySnapshotFrame",
        {
            "snapshot_id": frame.snapshot_id,
            "batch_id": frame.batch_id,
            "root_node_id": frame.root_node_id,
            "time_axis_node_id": frame.time_axis_node_id,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.schema_name != GRAPH_MEMORY_SNAPSHOT_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown graph snapshot schema_name: {frame.schema_name}")
    if frame.schema_version != GRAPH_MEMORY_SNAPSHOT_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown graph snapshot schema_version: {frame.schema_version}")
    if frame.generated_by != GRAPH_MEMORY_CODE_GENERATOR:
        raise ValueError("GraphMemorySnapshotFrame.generated_by must be code builder")
    if frame.info_class != "absolute":
        raise ValueError("GraphMemorySnapshotFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("GraphMemorySnapshotFrame.semantic_judgement_status must be not_run")
    _validate_string_list("GraphMemorySnapshotFrame.graph_node_ids", frame.graph_node_ids)
    _validate_string_list("GraphMemorySnapshotFrame.graph_edge_ids", frame.graph_edge_ids)
    _validate_string_list(
        "GraphMemorySnapshotFrame.source_graph_node_ids",
        frame.source_graph_node_ids,
    )
    _validate_string_list("GraphMemorySnapshotFrame.source_trace_ids", frame.source_trace_ids)
    _validate_string_list("GraphMemorySnapshotFrame.source_data_ids", frame.source_data_ids)
    _validate_no_duplicates("GraphMemorySnapshotFrame.graph_node_ids", frame.graph_node_ids)
    _validate_no_duplicates("GraphMemorySnapshotFrame.graph_edge_ids", frame.graph_edge_ids)
    _validate_no_duplicates(
        "GraphMemorySnapshotFrame.source_graph_node_ids",
        frame.source_graph_node_ids,
    )
    _validate_no_duplicates("GraphMemorySnapshotFrame.source_trace_ids", frame.source_trace_ids)
    _validate_no_duplicates("GraphMemorySnapshotFrame.source_data_ids", frame.source_data_ids)
    if frame.root_node_id not in frame.graph_node_ids:
        raise ValueError("GraphMemorySnapshotFrame.graph_node_ids must include root_node_id")
    if frame.time_axis_node_id not in frame.graph_node_ids:
        raise ValueError("GraphMemorySnapshotFrame.graph_node_ids must include time_axis_node_id")
    _validate_counts("GraphMemorySnapshotFrame.node_kind_counts", frame.node_kind_counts)
    _validate_counts("GraphMemorySnapshotFrame.edge_kind_counts", frame.edge_kind_counts)
    _validate_counts("GraphMemorySnapshotFrame.data_kind_counts", frame.data_kind_counts)


def validate_core_ego_time_axis_frame(frame: CoreEgoTimeAxisFrame) -> None:
    _require_text_fields(
        "CoreEgoTimeAxisFrame",
        {
            "frame_id": frame.frame_id,
            "batch_id": frame.batch_id,
            "core_ego_node_id": frame.core_ego_node_id,
            "time_axis_node_id": frame.time_axis_node_id,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "semantic_axis_status": frame.semantic_axis_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.schema_name != CORE_EGO_TIME_AXIS_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown CoreEgoTimeAxisFrame schema_name: {frame.schema_name}")
    if frame.schema_version != CORE_EGO_TIME_AXIS_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown CoreEgoTimeAxisFrame schema_version: {frame.schema_version}")
    if frame.generated_by != GRAPH_MEMORY_CODE_GENERATOR:
        raise ValueError("CoreEgoTimeAxisFrame.generated_by must be code builder")
    if frame.info_class != "absolute":
        raise ValueError("CoreEgoTimeAxisFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("CoreEgoTimeAxisFrame.semantic_judgement_status must be not_run")
    if frame.semantic_axis_status != "not_created":
        raise ValueError("CoreEgoTimeAxisFrame must not create semantic axis")
    _validate_string_list("CoreEgoTimeAxisFrame.time_bundle_node_ids", frame.time_bundle_node_ids)
    _validate_string_list("CoreEgoTimeAxisFrame.raw_capsule_node_ids", frame.raw_capsule_node_ids)
    _validate_string_list("CoreEgoTimeAxisFrame.edge_ids", frame.edge_ids)
    _validate_string_list(
        "CoreEgoTimeAxisFrame.source_graph_node_ids",
        frame.source_graph_node_ids,
    )
    _validate_string_list("CoreEgoTimeAxisFrame.source_trace_ids", frame.source_trace_ids)
    _validate_string_list("CoreEgoTimeAxisFrame.source_data_ids", frame.source_data_ids)
    _validate_no_duplicates(
        "CoreEgoTimeAxisFrame.time_bundle_node_ids",
        frame.time_bundle_node_ids,
    )
    _validate_no_duplicates(
        "CoreEgoTimeAxisFrame.raw_capsule_node_ids",
        frame.raw_capsule_node_ids,
    )
    _validate_no_duplicates("CoreEgoTimeAxisFrame.edge_ids", frame.edge_ids)


def validate_rloop_graph_guide_packet_frame(frame: RLoopGraphGuidePacketFrame) -> None:
    _require_text_fields(
        "RLoopGraphGuidePacketFrame",
        {
            "packet_id": frame.packet_id,
            "graph_snapshot_id": frame.graph_snapshot_id,
            "target_consumer": frame.target_consumer,
            "recommended_traversal_hints_status": frame.recommended_traversal_hints_status,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.schema_name != RLOOP_GRAPH_GUIDE_PACKET_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown RLoopGraphGuidePacketFrame schema_name: {frame.schema_name}")
    if frame.schema_version != RLOOP_GRAPH_GUIDE_PACKET_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown RLoopGraphGuidePacketFrame schema_version: {frame.schema_version}"
        )
    if frame.target_consumer != "R_LOOP":
        raise ValueError("RLoopGraphGuidePacketFrame.target_consumer must be R_LOOP")
    if frame.generated_by != RLOOP_GUIDE_CODE_GENERATOR:
        raise ValueError("RLoopGraphGuidePacketFrame.generated_by must be guide builder")
    if frame.info_class != "absolute":
        raise ValueError("RLoopGraphGuidePacketFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("RLoopGraphGuidePacketFrame.semantic_judgement_status must be not_run")
    if frame.recommended_traversal_hints_status != "not_run":
        raise ValueError("RLoopGraphGuidePacketFrame hints must remain not_run")
    if frame.recommended_traversal_hints:
        raise ValueError("RLoopGraphGuidePacketFrame must not include LLM traversal hints")

    _validate_string_list("RLoopGraphGuidePacketFrame.available_entry_nodes", frame.available_entry_nodes)
    _validate_string_list(
        "RLoopGraphGuidePacketFrame.risky_or_unreviewed_node_ids",
        frame.risky_or_unreviewed_node_ids,
    )
    _validate_string_list(
        "RLoopGraphGuidePacketFrame.source_graph_node_ids",
        frame.source_graph_node_ids,
    )
    _validate_string_list("RLoopGraphGuidePacketFrame.source_trace_ids", frame.source_trace_ids)
    _validate_string_list("RLoopGraphGuidePacketFrame.source_data_ids", frame.source_data_ids)
    _validate_no_duplicates(
        "RLoopGraphGuidePacketFrame.available_entry_nodes",
        frame.available_entry_nodes,
    )
    _validate_no_duplicates(
        "RLoopGraphGuidePacketFrame.source_graph_node_ids",
        frame.source_graph_node_ids,
    )
    _validate_no_duplicates("RLoopGraphGuidePacketFrame.source_trace_ids", frame.source_trace_ids)
    _validate_no_duplicates("RLoopGraphGuidePacketFrame.source_data_ids", frame.source_data_ids)
    _validate_counts("RLoopGraphGuidePacketFrame.node_kind_counts", frame.node_kind_counts)
    _validate_counts("RLoopGraphGuidePacketFrame.data_kind_counts", frame.data_kind_counts)
    _validate_range("RLoopGraphGuidePacketFrame.summary_depth_range", frame.summary_depth_range)
    _validate_range(
        "RLoopGraphGuidePacketFrame.source_leaf_count_range",
        frame.source_leaf_count_range,
    )


def _require_text_fields(frame_name: str, fields: dict[str, str | None]) -> None:
    for field_name, value in fields.items():
        if not value:
            raise ValueError(f"{frame_name}.{field_name} must not be empty")


def _validate_non_negative_ints(frame_name: str, fields: dict[str, int]) -> None:
    for field_name, value in fields.items():
        if value < 0:
            raise ValueError(f"{frame_name}.{field_name} must be >= 0")


def _validate_counts(field_name: str, counts: dict[str, int]) -> None:
    for key, value in counts.items():
        if not key:
            raise ValueError(f"{field_name} must not contain empty keys")
        if value < 0:
            raise ValueError(f"{field_name}.{key} must be >= 0")


def _validate_range(field_name: str, values: list[int]) -> None:
    if len(values) != 2:
        raise ValueError(f"{field_name} must contain [min, max]")
    if values[0] < 0 or values[1] < 0:
        raise ValueError(f"{field_name} values must be >= 0")
    if values[0] > values[1]:
        raise ValueError(f"{field_name} is inverted")


__all__ = [
    "CORE_EGO_TIME_AXIS_FRAME_SCHEMA_NAME",
    "CORE_EGO_TIME_AXIS_FRAME_SCHEMA_VERSION",
    "GRAPH_MEMORY_CODE_GENERATOR",
    "GRAPH_MEMORY_EDGE_FRAME_SCHEMA_NAME",
    "GRAPH_MEMORY_EDGE_FRAME_SCHEMA_VERSION",
    "GRAPH_MEMORY_EDGE_KINDS",
    "GRAPH_MEMORY_NODE_FRAME_SCHEMA_NAME",
    "GRAPH_MEMORY_NODE_FRAME_SCHEMA_VERSION",
    "GRAPH_MEMORY_NODE_KINDS",
    "GRAPH_MEMORY_SNAPSHOT_FRAME_SCHEMA_NAME",
    "GRAPH_MEMORY_SNAPSHOT_FRAME_SCHEMA_VERSION",
    "RLOOP_GRAPH_GUIDE_PACKET_FRAME_SCHEMA_NAME",
    "RLOOP_GRAPH_GUIDE_PACKET_FRAME_SCHEMA_VERSION",
    "RLOOP_GUIDE_CODE_GENERATOR",
    "CoreEgoTimeAxisFrame",
    "GraphMemoryEdgeFrame",
    "GraphMemoryNodeFrame",
    "GraphMemorySnapshotFrame",
    "RLoopGraphGuidePacketFrame",
    "validate_core_ego_time_axis_frame",
    "validate_graph_memory_edge_frame",
    "validate_graph_memory_node_frame",
    "validate_graph_memory_snapshot_frame",
    "validate_rloop_graph_guide_packet_frame",
]
