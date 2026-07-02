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
TURN_GRAPH_ACCESS_LEDGER_FRAME_SCHEMA_NAME = "TurnGraphAccessLedgerFrame"
TURN_GRAPH_ACCESS_LEDGER_FRAME_SCHEMA_VERSION = "0.1"
TURN_ACTIVITY_GRAPH_LINK_FRAME_SCHEMA_NAME = "TurnActivityGraphLinkFrame"
TURN_ACTIVITY_GRAPH_LINK_FRAME_SCHEMA_VERSION = "0.1"
CORE_EGO_TIME_AXIS_FRAME_SCHEMA_NAME = "CoreEgoTimeAxisFrame"
CORE_EGO_TIME_AXIS_FRAME_SCHEMA_VERSION = "0.1"
RLOOP_GRAPH_GUIDE_PACKET_FRAME_SCHEMA_NAME = "RLoopGraphGuidePacketFrame"
RLOOP_GRAPH_GUIDE_PACKET_FRAME_SCHEMA_VERSION = "0.1"
CORE_EGO_GUIDE_WORKER_HINT_FRAME_SCHEMA_NAME = "CoreEgoGuideWorkerHintFrame"
CORE_EGO_GUIDE_WORKER_HINT_FRAME_SCHEMA_VERSION = "0.1"
R_LOOP_MEMORY_HANDOFF_PACKET_FRAME_SCHEMA_NAME = "RLoopMemoryHandoffPacketFrame"
R_LOOP_MEMORY_HANDOFF_PACKET_FRAME_SCHEMA_VERSION = "0.1"
SOURCE_VERSION_LINEAGE_FRAME_SCHEMA_NAME = "SourceVersionLineageFrame"
SOURCE_VERSION_LINEAGE_FRAME_SCHEMA_VERSION = "0.1"
SOURCE_OBSERVATION_LEDGER_FRAME_SCHEMA_NAME = "SourceObservationLedgerFrame"
SOURCE_OBSERVATION_LEDGER_FRAME_SCHEMA_VERSION = "0.1"
SUMMARY_INVALIDATION_LEDGER_FRAME_SCHEMA_NAME = "SummaryInvalidationLedgerFrame"
SUMMARY_INVALIDATION_LEDGER_FRAME_SCHEMA_VERSION = "0.1"

GRAPH_MEMORY_NODE_KINDS = {
    "raw_capsule",
    "raw_bundle",
    "summary",
    "core_ego",
    "time_axis",
    "time_bundle",
    "activity_ledger",
    "raw_source",
    "source_ingest_time_bundle",
    "source_kind_bundle",
}
GRAPH_MEMORY_EDGE_KINDS = {
    "CONTAINS",
    "CHILD_OF_TIME_AXIS",
    "NEXT",
    "HAS_ACTIVITY_LEDGER",
    "SOURCE_OF",
    "SUMMARY_OF",
}
GRAPH_MEMORY_CODE_GENERATOR = "CODE:GRAPH_MEMORY_BUILDER"
GRAPH_ACCESS_LEDGER_CODE_GENERATOR = "CODE:GRAPH_ACCESS_LEDGER"
TURN_ACTIVITY_GRAPH_LINK_CODE_GENERATOR = "CODE:TURN_ACTIVITY_GRAPH_LINK_BUILDER"
RLOOP_GUIDE_CODE_GENERATOR = "CODE:GRAPH_MEMORY_GUIDE_BUILDER"
GRAPH_ACCESS_STAGES = {
    "candidate_seen",
    "selected",
    "inspected",
    "read",
    "used_as_answer_source",
}
CORE_EGO_GUIDE_WORKER_HINT_FAILURE_TYPES = {
    "none",
    "adapter_missing",
    "adapter_failed",
    "parse_failed",
    "schema_failed",
}
CORE_EGO_GUIDE_WORKER_HINT_STATUSES = {"ran", "failed"}
CORE_EGO_GUIDE_WORKER_PARSE_STATUSES = {"passed", "failed", "not_checked"}
R_LOOP_MEMORY_HANDOFF_STATUSES = {"available", "missing"}
R_LOOP_MEMORY_HANDOFF_SEMANTIC_HINT_STATUSES = {"not_run", "ran", "failed"}
TURN_ACTIVITY_GRAPH_LINK_ACTIVITY_KINDS = {
    "l_loop_activity_ledger",
    "r_graph_access_ledger",
}
SOURCE_VERSION_LINEAGE_CODE_GENERATOR = "CODE:SOURCE_VERSION_LINEAGE_BUILDER"
SOURCE_OBSERVATION_LEDGER_CODE_GENERATOR = "CODE:SOURCE_OBSERVATION_LEDGER_BUILDER"
SUMMARY_INVALIDATION_LEDGER_CODE_GENERATOR = "CODE:SUMMARY_INVALIDATION_LEDGER_BUILDER"
SOURCE_VERSION_LINEAGE_STATUSES = {
    "single_version",
    "content_changed",
}
SOURCE_OBSERVATION_LEDGER_STATUSES = {"no_observations", "recorded"}
SOURCE_OBSERVATION_STATUSES = {
    "new_source_version",
    "unchanged",
    "content_changed",
}
SUMMARY_INVALIDATION_LEDGER_STATUSES = {
    "no_invalidations",
    "invalidations_recorded",
}


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
    observed_at: str | None = None
    ingested_at: str | None = None
    source_last_modified_at: str | None = None
    exists_at_ingest: bool | None = None
    content_sha1: str | None = None
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
class TurnGraphAccessLedgerFrame:
    """A per-turn absolute ledger of graph nodes seen by an R traversal."""

    frame_id: str
    turn_id: str
    turn_capsule_graph_node_id: str
    candidate_graph_node_ids: list[str] = field(default_factory=list)
    selected_graph_node_ids: list[str] = field(default_factory=list)
    inspected_graph_node_ids: list[str] = field(default_factory=list)
    read_graph_node_ids: list[str] = field(default_factory=list)
    used_as_answer_source_graph_node_ids: list[str] = field(default_factory=list)
    access_records: list[dict[str, str]] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = GRAPH_ACCESS_LEDGER_CODE_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = TURN_GRAPH_ACCESS_LEDGER_FRAME_SCHEMA_NAME
    schema_version: str = TURN_GRAPH_ACCESS_LEDGER_FRAME_SCHEMA_VERSION


@dataclass
class TurnActivityGraphLinkFrame:
    """A code-generated graph link index from one raw capsule to activity ledgers."""

    frame_id: str
    turn_id: str
    turn_capsule_graph_node_id: str
    l_loop_activity_ledger_data_ids: list[str] = field(default_factory=list)
    r_graph_access_ledger_data_ids: list[str] = field(default_factory=list)
    activity_ledger_graph_node_ids: list[str] = field(default_factory=list)
    activity_ledger_graph_edge_ids: list[str] = field(default_factory=list)
    link_records: list[dict[str, str]] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = TURN_ACTIVITY_GRAPH_LINK_CODE_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = TURN_ACTIVITY_GRAPH_LINK_FRAME_SCHEMA_NAME
    schema_version: str = TURN_ACTIVITY_GRAPH_LINK_FRAME_SCHEMA_VERSION


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


@dataclass
class CoreEgoGuideWorkerHintFrame:
    """An LLM-generated traversal hint over a code-generated graph guide packet."""

    frame_id: str
    source_rloop_graph_guide_packet_id: str
    graph_snapshot_id: str
    available_entry_node_ids: list[str] = field(default_factory=list)
    available_source_graph_node_ids: list[str] = field(default_factory=list)
    recommended_entry_node_ids: list[str] = field(default_factory=list)
    avoid_entry_node_ids: list[str] = field(default_factory=list)
    traversal_strategy_hint: str = ""
    reason_summary: str = ""
    risk_notes: list[str] = field(default_factory=list)
    expected_depth_policy: str = ""
    hint_status: str = "failed"
    failure_type: str = "adapter_missing"
    payload_parse_status: str = "not_checked"
    llm_call_data_id: str | None = None
    llm_trace_event_id: str | None = None
    prompt_ref: str = ""
    source_graph_node_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = "LLM:unknown:core_ego_guide_worker"
    info_class: str = "mixed"
    source_mode: str = "source_bundle"
    claim_alignment: str = "multi_source_bundle"
    semantic_judgement_status: str = "failed"
    schema_name: str = CORE_EGO_GUIDE_WORKER_HINT_FRAME_SCHEMA_NAME
    schema_version: str = CORE_EGO_GUIDE_WORKER_HINT_FRAME_SCHEMA_VERSION


@dataclass
class RLoopMemoryHandoffPacketFrame:
    """A node_0 handoff packet that copies graph guide coordinates for a future R loop."""

    packet_id: str
    target: str = "R_LOOP"
    mode: str = "graph_guide_handoff"
    packet_status: str = "missing"
    graph_snapshot_id: str = ""
    r_loop_graph_guide_packet_id: str = ""
    available_entry_node_ids: list[str] = field(default_factory=list)
    node_kind_counts: dict[str, int] = field(default_factory=dict)
    data_kind_counts: dict[str, int] = field(default_factory=dict)
    summary_depth_range: list[int] = field(default_factory=lambda: [0, 0])
    source_leaf_count_range: list[int] = field(default_factory=lambda: [0, 0])
    semantic_hint_status: str = "not_run"
    semantic_hint_frame_id: str | None = None
    source_graph_node_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = "CODE:node_0_memory_supplier"
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R_LOOP_MEMORY_HANDOFF_PACKET_FRAME_SCHEMA_NAME
    schema_version: str = R_LOOP_MEMORY_HANDOFF_PACKET_FRAME_SCHEMA_VERSION


@dataclass
class SourceVersionLineageFrame:
    """A code-generated version lineage for one source_kind + path identity."""

    frame_id: str
    source_identity_key: str
    source_kind: str
    path: str
    lineage_status: str
    active_source_graph_node_id: str
    version_source_graph_node_ids: list[str] = field(default_factory=list)
    superseded_source_graph_node_ids: list[str] = field(default_factory=list)
    source_file_data_ids: list[str] = field(default_factory=list)
    version_records: list[dict[str, str]] = field(default_factory=list)
    content_sha1_by_version: dict[str, str] = field(default_factory=dict)
    observed_at_by_version: dict[str, str] = field(default_factory=dict)
    source_graph_node_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = SOURCE_VERSION_LINEAGE_CODE_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = SOURCE_VERSION_LINEAGE_FRAME_SCHEMA_NAME
    schema_version: str = SOURCE_VERSION_LINEAGE_FRAME_SCHEMA_VERSION


@dataclass
class SourceObservationLedgerFrame:
    """A code-generated ledger of source checks that do not always create versions."""

    frame_id: str
    batch_id: str
    ledger_status: str
    observation_records: list[dict[str, str]] = field(default_factory=list)
    observation_status_counts: dict[str, int] = field(default_factory=dict)
    observed_source_file_data_ids: list[str] = field(default_factory=list)
    active_source_graph_node_ids: list[str] = field(default_factory=list)
    source_graph_node_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = SOURCE_OBSERVATION_LEDGER_CODE_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = SOURCE_OBSERVATION_LEDGER_FRAME_SCHEMA_NAME
    schema_version: str = SOURCE_OBSERVATION_LEDGER_FRAME_SCHEMA_VERSION


@dataclass
class SummaryInvalidationLedgerFrame:
    """A code-generated ledger of summaries invalidated by source changes."""

    frame_id: str
    batch_id: str
    ledger_status: str
    invalidated_summary_node_ids: list[str] = field(default_factory=list)
    invalidation_records: list[dict[str, str]] = field(default_factory=list)
    changed_source_lineage_frame_ids: list[str] = field(default_factory=list)
    changed_source_graph_node_ids: list[str] = field(default_factory=list)
    active_source_graph_node_ids: list[str] = field(default_factory=list)
    source_graph_node_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = SUMMARY_INVALIDATION_LEDGER_CODE_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = SUMMARY_INVALIDATION_LEDGER_FRAME_SCHEMA_NAME
    schema_version: str = SUMMARY_INVALIDATION_LEDGER_FRAME_SCHEMA_VERSION


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
    if frame.node_kind == "raw_source":
        if frame.summary_depth != 0:
            raise ValueError("raw source summary_depth must be 0")
        if frame.source_leaf_count != 1:
            raise ValueError("raw source source_leaf_count must be 1")
        if frame.source_summary_count != 0:
            raise ValueError("raw source source_summary_count must be 0")
        if not frame.source_data_ids:
            raise ValueError("raw source graph node must cite source file data")
        if not frame.observed_at:
            raise ValueError("raw source graph node must include observed_at")
        if not frame.ingested_at:
            raise ValueError("raw source graph node must include ingested_at")
        if not frame.source_last_modified_at:
            raise ValueError("raw source graph node must include source_last_modified_at")
        if frame.exists_at_ingest is not True:
            raise ValueError("raw source graph node must have exists_at_ingest=True")
        if not frame.content_sha1:
            raise ValueError("raw source graph node must include content_sha1")
    if frame.node_kind == "source_ingest_time_bundle":
        if not frame.source_graph_node_ids:
            raise ValueError("source ingest time bundle must contain source kind bundles")
        if frame.source_leaf_count < len(frame.source_graph_node_ids):
            raise ValueError("source ingest time bundle source_leaf_count is too small")
        if not frame.observed_at:
            raise ValueError("source ingest time bundle must include observed_at")
        if not frame.ingested_at:
            raise ValueError("source ingest time bundle must include ingested_at")
    if frame.node_kind == "source_kind_bundle":
        if not frame.source_graph_node_ids:
            raise ValueError("source kind bundle must contain raw source graph nodes")
        if frame.source_leaf_count != len(frame.source_graph_node_ids):
            raise ValueError("source kind bundle source_leaf_count must mirror children")
        if not frame.observed_at:
            raise ValueError("source kind bundle must include observed_at")
        if not frame.ingested_at:
            raise ValueError("source kind bundle must include ingested_at")


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


def validate_turn_graph_access_ledger_frame(frame: TurnGraphAccessLedgerFrame) -> None:
    _require_text_fields(
        "TurnGraphAccessLedgerFrame",
        {
            "frame_id": frame.frame_id,
            "turn_id": frame.turn_id,
            "turn_capsule_graph_node_id": frame.turn_capsule_graph_node_id,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.schema_name != TURN_GRAPH_ACCESS_LEDGER_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown turn graph access ledger schema_name: {frame.schema_name}")
    if frame.schema_version != TURN_GRAPH_ACCESS_LEDGER_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown turn graph access ledger schema_version: {frame.schema_version}")
    if frame.generated_by != GRAPH_ACCESS_LEDGER_CODE_GENERATOR:
        raise ValueError("TurnGraphAccessLedgerFrame.generated_by must be graph access ledger code")
    if frame.info_class != "absolute":
        raise ValueError("TurnGraphAccessLedgerFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("TurnGraphAccessLedgerFrame.semantic_judgement_status must be not_run")

    graph_id_fields = {
        "candidate_graph_node_ids": frame.candidate_graph_node_ids,
        "selected_graph_node_ids": frame.selected_graph_node_ids,
        "inspected_graph_node_ids": frame.inspected_graph_node_ids,
        "read_graph_node_ids": frame.read_graph_node_ids,
        "used_as_answer_source_graph_node_ids": frame.used_as_answer_source_graph_node_ids,
    }
    for field_name, values in graph_id_fields.items():
        _validate_string_list(f"TurnGraphAccessLedgerFrame.{field_name}", values)
        _validate_no_duplicates(f"TurnGraphAccessLedgerFrame.{field_name}", values)
    _validate_string_list("TurnGraphAccessLedgerFrame.source_trace_ids", frame.source_trace_ids)
    _validate_string_list("TurnGraphAccessLedgerFrame.source_data_ids", frame.source_data_ids)
    _validate_no_duplicates("TurnGraphAccessLedgerFrame.source_trace_ids", frame.source_trace_ids)
    _validate_no_duplicates("TurnGraphAccessLedgerFrame.source_data_ids", frame.source_data_ids)

    known_graph_node_ids = {
        frame.turn_capsule_graph_node_id,
        *frame.candidate_graph_node_ids,
        *frame.selected_graph_node_ids,
        *frame.inspected_graph_node_ids,
        *frame.read_graph_node_ids,
        *frame.used_as_answer_source_graph_node_ids,
    }
    if not frame.access_records:
        raise ValueError("TurnGraphAccessLedgerFrame.access_records must not be empty")
    for index, record in enumerate(frame.access_records, start=1):
        if not isinstance(record, dict):
            raise ValueError("TurnGraphAccessLedgerFrame.access_records must contain dict records")
        stage = record.get("stage")
        graph_node_id = record.get("graph_node_id")
        source_frame_id = record.get("source_frame_id")
        source_field = record.get("source_field")
        if not stage or not graph_node_id or not source_frame_id or not source_field:
            raise ValueError(
                "TurnGraphAccessLedgerFrame.access_records entries require "
                "stage, graph_node_id, source_frame_id, source_field"
            )
        if stage not in GRAPH_ACCESS_STAGES:
            raise ValueError(f"unknown graph access stage: {stage}")
        if graph_node_id not in known_graph_node_ids:
            raise ValueError(
                "TurnGraphAccessLedgerFrame.access_records graph_node_id must be listed "
                f"in ledger graph node fields at index {index}"
            )
        if source_frame_id not in frame.source_data_ids:
            raise ValueError(
                "TurnGraphAccessLedgerFrame.source_data_ids must include access record source_frame_id"
            )


def validate_turn_activity_graph_link_frame(frame: TurnActivityGraphLinkFrame) -> None:
    _require_text_fields(
        "TurnActivityGraphLinkFrame",
        {
            "frame_id": frame.frame_id,
            "turn_id": frame.turn_id,
            "turn_capsule_graph_node_id": frame.turn_capsule_graph_node_id,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.schema_name != TURN_ACTIVITY_GRAPH_LINK_FRAME_SCHEMA_NAME:
        raise ValueError(
            f"unknown TurnActivityGraphLinkFrame.schema_name: {frame.schema_name}"
        )
    if frame.schema_version != TURN_ACTIVITY_GRAPH_LINK_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown TurnActivityGraphLinkFrame.schema_version: {frame.schema_version}"
        )
    if frame.generated_by != TURN_ACTIVITY_GRAPH_LINK_CODE_GENERATOR:
        raise ValueError("TurnActivityGraphLinkFrame.generated_by must reveal code builder")
    if frame.info_class != "absolute":
        raise ValueError("TurnActivityGraphLinkFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("TurnActivityGraphLinkFrame.semantic_judgement_status must be not_run")

    list_fields = {
        "l_loop_activity_ledger_data_ids": frame.l_loop_activity_ledger_data_ids,
        "r_graph_access_ledger_data_ids": frame.r_graph_access_ledger_data_ids,
        "activity_ledger_graph_node_ids": frame.activity_ledger_graph_node_ids,
        "activity_ledger_graph_edge_ids": frame.activity_ledger_graph_edge_ids,
        "source_trace_ids": frame.source_trace_ids,
        "source_data_ids": frame.source_data_ids,
    }
    for field_name, values in list_fields.items():
        _validate_string_list(f"TurnActivityGraphLinkFrame.{field_name}", values)
        _validate_no_duplicates(f"TurnActivityGraphLinkFrame.{field_name}", values)

    ledger_data_ids = {
        *frame.l_loop_activity_ledger_data_ids,
        *frame.r_graph_access_ledger_data_ids,
    }
    if len(frame.activity_ledger_graph_node_ids) != len(ledger_data_ids):
        raise ValueError(
            "TurnActivityGraphLinkFrame.activity_ledger_graph_node_ids must mirror ledger count"
        )
    if len(frame.activity_ledger_graph_edge_ids) != len(ledger_data_ids):
        raise ValueError(
            "TurnActivityGraphLinkFrame.activity_ledger_graph_edge_ids must mirror ledger count"
        )
    if len(frame.link_records) != len(ledger_data_ids):
        raise ValueError("TurnActivityGraphLinkFrame.link_records must mirror ledger count")

    source_data_ids = set(frame.source_data_ids)
    required_sources = {
        frame.turn_capsule_graph_node_id,
        *ledger_data_ids,
        *frame.activity_ledger_graph_node_ids,
        *frame.activity_ledger_graph_edge_ids,
    }
    if not required_sources <= source_data_ids:
        missing = sorted(required_sources - source_data_ids)
        raise ValueError(
            "TurnActivityGraphLinkFrame.source_data_ids must include graph/link sources: "
            f"{missing}"
        )

    node_ids = set(frame.activity_ledger_graph_node_ids)
    edge_ids = set(frame.activity_ledger_graph_edge_ids)
    for index, record in enumerate(frame.link_records, start=1):
        if not isinstance(record, dict):
            raise ValueError("TurnActivityGraphLinkFrame.link_records must contain dict records")
        activity_kind = record.get("activity_kind")
        ledger_data_id = record.get("ledger_data_id")
        graph_node_id = record.get("graph_node_id")
        edge_id = record.get("edge_id")
        source_field = record.get("source_field")
        if not activity_kind or not ledger_data_id or not graph_node_id or not edge_id or not source_field:
            raise ValueError(
                "TurnActivityGraphLinkFrame.link_records entries require "
                "activity_kind, ledger_data_id, graph_node_id, edge_id, source_field"
            )
        if activity_kind not in TURN_ACTIVITY_GRAPH_LINK_ACTIVITY_KINDS:
            raise ValueError(f"unknown turn activity graph link kind: {activity_kind}")
        if ledger_data_id not in ledger_data_ids:
            raise ValueError(
                f"TurnActivityGraphLinkFrame.link_records ledger_data_id is not listed at {index}"
            )
        if graph_node_id not in node_ids:
            raise ValueError(
                f"TurnActivityGraphLinkFrame.link_records graph_node_id is not listed at {index}"
            )
        if edge_id not in edge_ids:
            raise ValueError(
                f"TurnActivityGraphLinkFrame.link_records edge_id is not listed at {index}"
            )


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


def validate_core_ego_guide_worker_hint_frame(frame: CoreEgoGuideWorkerHintFrame) -> None:
    _require_text_fields(
        "CoreEgoGuideWorkerHintFrame",
        {
            "frame_id": frame.frame_id,
            "source_rloop_graph_guide_packet_id": frame.source_rloop_graph_guide_packet_id,
            "graph_snapshot_id": frame.graph_snapshot_id,
            "hint_status": frame.hint_status,
            "failure_type": frame.failure_type,
            "payload_parse_status": frame.payload_parse_status,
            "prompt_ref": frame.prompt_ref,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "source_mode": frame.source_mode,
            "claim_alignment": frame.claim_alignment,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.schema_name != CORE_EGO_GUIDE_WORKER_HINT_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown CoreEgoGuideWorkerHintFrame schema_name: {frame.schema_name}")
    if frame.schema_version != CORE_EGO_GUIDE_WORKER_HINT_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown CoreEgoGuideWorkerHintFrame schema_version: {frame.schema_version}"
        )
    if frame.hint_status not in CORE_EGO_GUIDE_WORKER_HINT_STATUSES:
        raise ValueError(f"unknown CoreEgoGuideWorkerHintFrame.hint_status: {frame.hint_status}")
    if frame.failure_type not in CORE_EGO_GUIDE_WORKER_HINT_FAILURE_TYPES:
        raise ValueError(f"unknown CoreEgoGuideWorkerHintFrame.failure_type: {frame.failure_type}")
    if frame.payload_parse_status not in CORE_EGO_GUIDE_WORKER_PARSE_STATUSES:
        raise ValueError(
            f"unknown CoreEgoGuideWorkerHintFrame.payload_parse_status: {frame.payload_parse_status}"
        )
    if not frame.generated_by.startswith("LLM:"):
        raise ValueError("CoreEgoGuideWorkerHintFrame.generated_by must start with LLM:")
    if frame.info_class != "mixed":
        raise ValueError("CoreEgoGuideWorkerHintFrame.info_class must be mixed")
    if frame.source_mode != "source_bundle":
        raise ValueError("CoreEgoGuideWorkerHintFrame.source_mode must be source_bundle")
    if frame.claim_alignment != "multi_source_bundle":
        raise ValueError("CoreEgoGuideWorkerHintFrame.claim_alignment must be multi_source_bundle")
    if frame.semantic_judgement_status not in {"ran", "failed"}:
        raise ValueError(
            "CoreEgoGuideWorkerHintFrame.semantic_judgement_status must be ran or failed"
        )

    _validate_string_list(
        "CoreEgoGuideWorkerHintFrame.available_entry_node_ids",
        frame.available_entry_node_ids,
    )
    _validate_string_list(
        "CoreEgoGuideWorkerHintFrame.available_source_graph_node_ids",
        frame.available_source_graph_node_ids,
    )
    _validate_string_list(
        "CoreEgoGuideWorkerHintFrame.recommended_entry_node_ids",
        frame.recommended_entry_node_ids,
    )
    _validate_string_list(
        "CoreEgoGuideWorkerHintFrame.avoid_entry_node_ids",
        frame.avoid_entry_node_ids,
    )
    _validate_string_list("CoreEgoGuideWorkerHintFrame.risk_notes", frame.risk_notes)
    _validate_string_list(
        "CoreEgoGuideWorkerHintFrame.source_graph_node_ids",
        frame.source_graph_node_ids,
    )
    _validate_string_list("CoreEgoGuideWorkerHintFrame.source_trace_ids", frame.source_trace_ids)
    _validate_string_list("CoreEgoGuideWorkerHintFrame.source_data_ids", frame.source_data_ids)
    _validate_no_duplicates(
        "CoreEgoGuideWorkerHintFrame.available_entry_node_ids",
        frame.available_entry_node_ids,
    )
    _validate_no_duplicates(
        "CoreEgoGuideWorkerHintFrame.available_source_graph_node_ids",
        frame.available_source_graph_node_ids,
    )
    _validate_no_duplicates(
        "CoreEgoGuideWorkerHintFrame.recommended_entry_node_ids",
        frame.recommended_entry_node_ids,
    )
    _validate_no_duplicates(
        "CoreEgoGuideWorkerHintFrame.avoid_entry_node_ids",
        frame.avoid_entry_node_ids,
    )
    _validate_no_duplicates(
        "CoreEgoGuideWorkerHintFrame.source_graph_node_ids",
        frame.source_graph_node_ids,
    )
    _validate_no_duplicates("CoreEgoGuideWorkerHintFrame.source_trace_ids", frame.source_trace_ids)
    _validate_no_duplicates("CoreEgoGuideWorkerHintFrame.source_data_ids", frame.source_data_ids)

    available_entries = set(frame.available_entry_node_ids)
    for node_id in [*frame.recommended_entry_node_ids, *frame.avoid_entry_node_ids]:
        if node_id not in available_entries:
            raise ValueError("CoreEgoGuideWorkerHintFrame entry node id must be available")

    available_source_nodes = set(frame.available_source_graph_node_ids)
    for node_id in frame.source_graph_node_ids:
        if node_id not in available_source_nodes:
            raise ValueError("CoreEgoGuideWorkerHintFrame source_graph_node_ids must be in snapshot")

    if frame.source_rloop_graph_guide_packet_id not in frame.source_data_ids:
        raise ValueError(
            "CoreEgoGuideWorkerHintFrame.source_data_ids must include source guide packet"
        )
    if frame.graph_snapshot_id not in frame.source_data_ids:
        raise ValueError("CoreEgoGuideWorkerHintFrame.source_data_ids must include graph_snapshot_id")
    if frame.llm_call_data_id is not None:
        if not frame.llm_call_data_id:
            raise ValueError("CoreEgoGuideWorkerHintFrame.llm_call_data_id must not be empty")
        if frame.llm_call_data_id not in frame.source_data_ids:
            raise ValueError("CoreEgoGuideWorkerHintFrame.source_data_ids must include llm_call_data_id")
    if frame.llm_trace_event_id is not None:
        if not frame.llm_trace_event_id:
            raise ValueError("CoreEgoGuideWorkerHintFrame.llm_trace_event_id must not be empty")
        if frame.llm_trace_event_id not in frame.source_trace_ids:
            raise ValueError(
                "CoreEgoGuideWorkerHintFrame.source_trace_ids must include llm_trace_event_id"
            )

    if frame.hint_status == "ran":
        if frame.semantic_judgement_status != "ran":
            raise ValueError("ran CoreEgoGuideWorkerHintFrame must have semantic_judgement_status=ran")
        if frame.failure_type != "none":
            raise ValueError("ran CoreEgoGuideWorkerHintFrame must have failure_type=none")
        if frame.payload_parse_status != "passed":
            raise ValueError("ran CoreEgoGuideWorkerHintFrame must have payload_parse_status=passed")
        if not frame.traversal_strategy_hint.strip():
            raise ValueError("CoreEgoGuideWorkerHintFrame.traversal_strategy_hint must not be empty")
        if not frame.reason_summary.strip():
            raise ValueError("CoreEgoGuideWorkerHintFrame.reason_summary must not be empty")
        if not frame.expected_depth_policy.strip():
            raise ValueError("CoreEgoGuideWorkerHintFrame.expected_depth_policy must not be empty")
        if not frame.source_graph_node_ids:
            raise ValueError("ran CoreEgoGuideWorkerHintFrame.source_graph_node_ids must not be empty")
        return

    if frame.semantic_judgement_status != "failed":
        raise ValueError("failed CoreEgoGuideWorkerHintFrame must have semantic_judgement_status=failed")
    if frame.failure_type == "none":
        raise ValueError("failed CoreEgoGuideWorkerHintFrame must include failure_type")
    if frame.recommended_entry_node_ids or frame.avoid_entry_node_ids:
        raise ValueError("failed CoreEgoGuideWorkerHintFrame must not include recommendations")


def validate_r_loop_memory_handoff_packet_frame(frame: RLoopMemoryHandoffPacketFrame) -> None:
    _require_text_fields(
        "RLoopMemoryHandoffPacketFrame",
        {
            "packet_id": frame.packet_id,
            "target": frame.target,
            "mode": frame.mode,
            "packet_status": frame.packet_status,
            "semantic_hint_status": frame.semantic_hint_status,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.schema_name != R_LOOP_MEMORY_HANDOFF_PACKET_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown RLoopMemoryHandoffPacketFrame schema_name: {frame.schema_name}")
    if frame.schema_version != R_LOOP_MEMORY_HANDOFF_PACKET_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown RLoopMemoryHandoffPacketFrame schema_version: {frame.schema_version}"
        )
    if frame.target != "R_LOOP":
        raise ValueError("RLoopMemoryHandoffPacketFrame.target must be R_LOOP")
    if frame.mode != "graph_guide_handoff":
        raise ValueError("RLoopMemoryHandoffPacketFrame.mode must be graph_guide_handoff")
    if frame.packet_status not in R_LOOP_MEMORY_HANDOFF_STATUSES:
        raise ValueError(f"unknown RLoopMemoryHandoffPacketFrame.packet_status: {frame.packet_status}")
    if frame.semantic_hint_status not in R_LOOP_MEMORY_HANDOFF_SEMANTIC_HINT_STATUSES:
        raise ValueError(
            f"unknown RLoopMemoryHandoffPacketFrame.semantic_hint_status: {frame.semantic_hint_status}"
        )
    if frame.generated_by != "CODE:node_0_memory_supplier":
        raise ValueError("RLoopMemoryHandoffPacketFrame.generated_by must be node_0 code")
    if frame.info_class != "absolute":
        raise ValueError("RLoopMemoryHandoffPacketFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("RLoopMemoryHandoffPacketFrame.semantic_judgement_status must be not_run")

    _validate_string_list(
        "RLoopMemoryHandoffPacketFrame.available_entry_node_ids",
        frame.available_entry_node_ids,
    )
    _validate_string_list(
        "RLoopMemoryHandoffPacketFrame.source_graph_node_ids",
        frame.source_graph_node_ids,
    )
    _validate_string_list("RLoopMemoryHandoffPacketFrame.source_trace_ids", frame.source_trace_ids)
    _validate_string_list("RLoopMemoryHandoffPacketFrame.source_data_ids", frame.source_data_ids)
    _validate_no_duplicates(
        "RLoopMemoryHandoffPacketFrame.available_entry_node_ids",
        frame.available_entry_node_ids,
    )
    _validate_no_duplicates(
        "RLoopMemoryHandoffPacketFrame.source_graph_node_ids",
        frame.source_graph_node_ids,
    )
    _validate_no_duplicates("RLoopMemoryHandoffPacketFrame.source_trace_ids", frame.source_trace_ids)
    _validate_no_duplicates("RLoopMemoryHandoffPacketFrame.source_data_ids", frame.source_data_ids)
    _validate_counts("RLoopMemoryHandoffPacketFrame.node_kind_counts", frame.node_kind_counts)
    _validate_counts("RLoopMemoryHandoffPacketFrame.data_kind_counts", frame.data_kind_counts)
    _validate_range("RLoopMemoryHandoffPacketFrame.summary_depth_range", frame.summary_depth_range)
    _validate_range(
        "RLoopMemoryHandoffPacketFrame.source_leaf_count_range",
        frame.source_leaf_count_range,
    )

    if frame.packet_status == "available":
        if not frame.graph_snapshot_id:
            raise ValueError("available RLoopMemoryHandoffPacketFrame must include graph_snapshot_id")
        if not frame.r_loop_graph_guide_packet_id:
            raise ValueError(
                "available RLoopMemoryHandoffPacketFrame must include r_loop_graph_guide_packet_id"
            )
        if not frame.available_entry_node_ids:
            raise ValueError("available RLoopMemoryHandoffPacketFrame must include entry nodes")
        if not frame.source_graph_node_ids:
            raise ValueError("available RLoopMemoryHandoffPacketFrame must include source graph nodes")
        if frame.graph_snapshot_id not in frame.source_data_ids:
            raise ValueError(
                "RLoopMemoryHandoffPacketFrame.source_data_ids must include graph_snapshot_id"
            )
        if frame.r_loop_graph_guide_packet_id not in frame.source_data_ids:
            raise ValueError(
                "RLoopMemoryHandoffPacketFrame.source_data_ids must include guide packet id"
            )
    else:
        if frame.graph_snapshot_id or frame.r_loop_graph_guide_packet_id:
            raise ValueError("missing RLoopMemoryHandoffPacketFrame must not cite graph guide IDs")
        if frame.available_entry_node_ids or frame.source_graph_node_ids:
            raise ValueError("missing RLoopMemoryHandoffPacketFrame must not include graph nodes")

    if frame.semantic_hint_status in {"ran", "failed"}:
        if not frame.semantic_hint_frame_id:
            raise ValueError("semantic hint status ran/failed requires semantic_hint_frame_id")
        if frame.semantic_hint_frame_id not in frame.source_data_ids:
            raise ValueError(
                "RLoopMemoryHandoffPacketFrame.source_data_ids must include semantic_hint_frame_id"
            )


def validate_source_version_lineage_frame(frame: SourceVersionLineageFrame) -> None:
    _require_text_fields(
        "SourceVersionLineageFrame",
        {
            "frame_id": frame.frame_id,
            "source_identity_key": frame.source_identity_key,
            "source_kind": frame.source_kind,
            "path": frame.path,
            "lineage_status": frame.lineage_status,
            "active_source_graph_node_id": frame.active_source_graph_node_id,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.schema_name != SOURCE_VERSION_LINEAGE_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown SourceVersionLineageFrame.schema_name: {frame.schema_name}")
    if frame.schema_version != SOURCE_VERSION_LINEAGE_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown SourceVersionLineageFrame.schema_version: {frame.schema_version}"
        )
    if frame.generated_by != SOURCE_VERSION_LINEAGE_CODE_GENERATOR:
        raise ValueError("SourceVersionLineageFrame.generated_by must be code builder")
    if frame.info_class != "absolute":
        raise ValueError("SourceVersionLineageFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("SourceVersionLineageFrame.semantic_judgement_status must be not_run")
    if frame.lineage_status not in SOURCE_VERSION_LINEAGE_STATUSES:
        raise ValueError(f"unknown SourceVersionLineageFrame.lineage_status: {frame.lineage_status}")

    _validate_string_list(
        "SourceVersionLineageFrame.version_source_graph_node_ids",
        frame.version_source_graph_node_ids,
    )
    _validate_string_list(
        "SourceVersionLineageFrame.superseded_source_graph_node_ids",
        frame.superseded_source_graph_node_ids,
    )
    _validate_string_list("SourceVersionLineageFrame.source_file_data_ids", frame.source_file_data_ids)
    _validate_string_list(
        "SourceVersionLineageFrame.source_graph_node_ids",
        frame.source_graph_node_ids,
    )
    _validate_string_list("SourceVersionLineageFrame.source_trace_ids", frame.source_trace_ids)
    _validate_string_list("SourceVersionLineageFrame.source_data_ids", frame.source_data_ids)
    _validate_no_duplicates(
        "SourceVersionLineageFrame.version_source_graph_node_ids",
        frame.version_source_graph_node_ids,
    )
    _validate_no_duplicates(
        "SourceVersionLineageFrame.superseded_source_graph_node_ids",
        frame.superseded_source_graph_node_ids,
    )
    _validate_no_duplicates("SourceVersionLineageFrame.source_file_data_ids", frame.source_file_data_ids)
    _validate_no_duplicates(
        "SourceVersionLineageFrame.source_graph_node_ids",
        frame.source_graph_node_ids,
    )
    _validate_no_duplicates("SourceVersionLineageFrame.source_trace_ids", frame.source_trace_ids)
    _validate_no_duplicates("SourceVersionLineageFrame.source_data_ids", frame.source_data_ids)

    if not frame.version_source_graph_node_ids:
        raise ValueError("SourceVersionLineageFrame must include at least one source version")
    if frame.active_source_graph_node_id not in frame.version_source_graph_node_ids:
        raise ValueError("SourceVersionLineageFrame.active_source_graph_node_id must be a version")
    version_set = set(frame.version_source_graph_node_ids)
    superseded_set = set(frame.superseded_source_graph_node_ids)
    if not superseded_set.issubset(version_set):
        raise ValueError("SourceVersionLineageFrame superseded versions must be in version list")
    if frame.active_source_graph_node_id in superseded_set:
        raise ValueError("SourceVersionLineageFrame active version must not be superseded")
    if set(frame.source_graph_node_ids) != version_set:
        raise ValueError("SourceVersionLineageFrame.source_graph_node_ids must mirror versions")
    if not set(frame.source_file_data_ids).issubset(set(frame.source_data_ids)):
        raise ValueError("SourceVersionLineageFrame.source_data_ids must include source_file_data_ids")

    if len(frame.version_records) != len(frame.version_source_graph_node_ids):
        raise ValueError("SourceVersionLineageFrame.version_records must mirror versions")
    required_record_fields = {
        "version_index",
        "source_graph_node_id",
        "source_file_data_id",
        "content_sha1",
        "observed_at",
        "ingested_at",
        "source_last_modified_at",
        "supersedes_source_graph_node_id",
    }
    for record in frame.version_records:
        if not isinstance(record, dict):
            raise TypeError("SourceVersionLineageFrame.version_records items must be dicts")
        missing = required_record_fields - set(record)
        if missing:
            raise ValueError(
                "SourceVersionLineageFrame.version_records missing fields: "
                + ", ".join(sorted(missing))
            )
        for field_name, value in record.items():
            if not isinstance(value, str):
                raise TypeError(
                    f"SourceVersionLineageFrame.version_records.{field_name} must be string"
                )
        if record["source_graph_node_id"] not in version_set:
            raise ValueError("SourceVersionLineageFrame record source_graph_node_id unknown")
        if record["source_file_data_id"] not in frame.source_file_data_ids:
            raise ValueError("SourceVersionLineageFrame record source_file_data_id unknown")
        if not record["content_sha1"]:
            raise ValueError("SourceVersionLineageFrame record content_sha1 must not be empty")
        if not record["observed_at"]:
            raise ValueError("SourceVersionLineageFrame record observed_at must not be empty")

    if set(frame.content_sha1_by_version) != version_set:
        raise ValueError("SourceVersionLineageFrame.content_sha1_by_version must mirror versions")
    if set(frame.observed_at_by_version) != version_set:
        raise ValueError("SourceVersionLineageFrame.observed_at_by_version must mirror versions")
    for value in [*frame.content_sha1_by_version.values(), *frame.observed_at_by_version.values()]:
        if not value:
            raise ValueError("SourceVersionLineageFrame version maps must not contain empty values")


def validate_source_observation_ledger_frame(frame: SourceObservationLedgerFrame) -> None:
    _require_text_fields(
        "SourceObservationLedgerFrame",
        {
            "frame_id": frame.frame_id,
            "batch_id": frame.batch_id,
            "ledger_status": frame.ledger_status,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.schema_name != SOURCE_OBSERVATION_LEDGER_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown SourceObservationLedgerFrame.schema_name: {frame.schema_name}")
    if frame.schema_version != SOURCE_OBSERVATION_LEDGER_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown SourceObservationLedgerFrame.schema_version: {frame.schema_version}"
        )
    if frame.generated_by != SOURCE_OBSERVATION_LEDGER_CODE_GENERATOR:
        raise ValueError("SourceObservationLedgerFrame.generated_by must be code builder")
    if frame.info_class != "absolute":
        raise ValueError("SourceObservationLedgerFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("SourceObservationLedgerFrame.semantic_judgement_status must be not_run")
    if frame.ledger_status not in SOURCE_OBSERVATION_LEDGER_STATUSES:
        raise ValueError(f"unknown SourceObservationLedgerFrame.ledger_status: {frame.ledger_status}")

    for field_name, values in {
        "observed_source_file_data_ids": frame.observed_source_file_data_ids,
        "active_source_graph_node_ids": frame.active_source_graph_node_ids,
        "source_graph_node_ids": frame.source_graph_node_ids,
        "source_trace_ids": frame.source_trace_ids,
        "source_data_ids": frame.source_data_ids,
    }.items():
        _validate_string_list(f"SourceObservationLedgerFrame.{field_name}", values)
        _validate_no_duplicates(f"SourceObservationLedgerFrame.{field_name}", values)

    _validate_counts(
        "SourceObservationLedgerFrame.observation_status_counts",
        frame.observation_status_counts,
    )
    for key in frame.observation_status_counts:
        if key not in SOURCE_OBSERVATION_STATUSES:
            raise ValueError(f"unknown SourceObservationLedgerFrame status count key: {key}")

    if frame.ledger_status == "no_observations":
        if frame.observation_records or frame.observed_source_file_data_ids:
            raise ValueError("no_observations ledger must not include observation records")
    if frame.ledger_status == "recorded":
        if not frame.observation_records:
            raise ValueError("recorded SourceObservationLedgerFrame must include records")
        if not frame.observed_source_file_data_ids:
            raise ValueError("recorded SourceObservationLedgerFrame must include source file ids")

    required_record_fields = {
        "source_file_data_id",
        "source_kind",
        "path",
        "observed_at",
        "content_sha1",
        "observation_status",
        "active_source_graph_node_id",
        "previous_active_source_graph_node_id",
    }
    for record in frame.observation_records:
        if not isinstance(record, dict):
            raise TypeError("SourceObservationLedgerFrame.observation_records items must be dicts")
        missing = required_record_fields - set(record)
        if missing:
            raise ValueError(
                "SourceObservationLedgerFrame.observation_records missing fields: "
                + ", ".join(sorted(missing))
            )
        for field_name, value in record.items():
            if not isinstance(value, str):
                raise TypeError(
                    f"SourceObservationLedgerFrame.observation_records.{field_name} must be string"
                )
        for field_name in required_record_fields - {"previous_active_source_graph_node_id"}:
            if not record[field_name]:
                raise ValueError(
                    f"SourceObservationLedgerFrame.observation_records.{field_name} must not be empty"
                )
        if record["observation_status"] not in SOURCE_OBSERVATION_STATUSES:
            raise ValueError(
                f"unknown SourceObservationLedgerFrame observation_status: {record['observation_status']}"
            )
        if record["source_file_data_id"] not in frame.observed_source_file_data_ids:
            raise ValueError("SourceObservationLedgerFrame record source_file_data_id not listed")
        if record["active_source_graph_node_id"] not in frame.active_source_graph_node_ids:
            raise ValueError("SourceObservationLedgerFrame record active source id not listed")
        if record["active_source_graph_node_id"] not in frame.source_graph_node_ids:
            raise ValueError("SourceObservationLedgerFrame source_graph_node_ids missing active id")

    counted = _count_observation_statuses(frame.observation_records)
    if counted != frame.observation_status_counts:
        raise ValueError("SourceObservationLedgerFrame.observation_status_counts mismatch")


def validate_summary_invalidation_ledger_frame(frame: SummaryInvalidationLedgerFrame) -> None:
    _require_text_fields(
        "SummaryInvalidationLedgerFrame",
        {
            "frame_id": frame.frame_id,
            "batch_id": frame.batch_id,
            "ledger_status": frame.ledger_status,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.schema_name != SUMMARY_INVALIDATION_LEDGER_FRAME_SCHEMA_NAME:
        raise ValueError(
            f"unknown SummaryInvalidationLedgerFrame.schema_name: {frame.schema_name}"
        )
    if frame.schema_version != SUMMARY_INVALIDATION_LEDGER_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown SummaryInvalidationLedgerFrame.schema_version: {frame.schema_version}"
        )
    if frame.generated_by != SUMMARY_INVALIDATION_LEDGER_CODE_GENERATOR:
        raise ValueError("SummaryInvalidationLedgerFrame.generated_by must be code builder")
    if frame.info_class != "absolute":
        raise ValueError("SummaryInvalidationLedgerFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError(
            "SummaryInvalidationLedgerFrame.semantic_judgement_status must be not_run"
        )
    if frame.ledger_status not in SUMMARY_INVALIDATION_LEDGER_STATUSES:
        raise ValueError(
            f"unknown SummaryInvalidationLedgerFrame.ledger_status: {frame.ledger_status}"
        )

    for field_name, values in {
        "invalidated_summary_node_ids": frame.invalidated_summary_node_ids,
        "changed_source_lineage_frame_ids": frame.changed_source_lineage_frame_ids,
        "changed_source_graph_node_ids": frame.changed_source_graph_node_ids,
        "active_source_graph_node_ids": frame.active_source_graph_node_ids,
        "source_graph_node_ids": frame.source_graph_node_ids,
        "source_trace_ids": frame.source_trace_ids,
        "source_data_ids": frame.source_data_ids,
    }.items():
        _validate_string_list(f"SummaryInvalidationLedgerFrame.{field_name}", values)
        _validate_no_duplicates(f"SummaryInvalidationLedgerFrame.{field_name}", values)

    if frame.ledger_status == "no_invalidations":
        if frame.invalidated_summary_node_ids or frame.invalidation_records:
            raise ValueError("no_invalidations ledger must not include invalidation records")
    if frame.ledger_status == "invalidations_recorded":
        if not frame.invalidated_summary_node_ids:
            raise ValueError("invalidations_recorded ledger must include summary ids")
        if not frame.invalidation_records:
            raise ValueError("invalidations_recorded ledger must include records")

    required_record_fields = {
        "summary_graph_node_id",
        "invalidated_reason_code",
        "source_lineage_frame_id",
        "superseded_source_graph_node_id",
        "superseding_source_graph_node_id",
        "invalidated_at",
        "validity_status",
    }
    for record in frame.invalidation_records:
        if not isinstance(record, dict):
            raise TypeError("SummaryInvalidationLedgerFrame.invalidation_records items must be dicts")
        missing = required_record_fields - set(record)
        if missing:
            raise ValueError(
                "SummaryInvalidationLedgerFrame.invalidation_records missing fields: "
                + ", ".join(sorted(missing))
            )
        for field_name, value in record.items():
            if not isinstance(value, str):
                raise TypeError(
                    f"SummaryInvalidationLedgerFrame.invalidation_records.{field_name} must be string"
                )
            if not value:
                raise ValueError(
                    f"SummaryInvalidationLedgerFrame.invalidation_records.{field_name} must not be empty"
                )
        if record["summary_graph_node_id"] not in frame.invalidated_summary_node_ids:
            raise ValueError("SummaryInvalidationLedgerFrame record summary id not listed")
        if record["source_lineage_frame_id"] not in frame.changed_source_lineage_frame_ids:
            raise ValueError("SummaryInvalidationLedgerFrame record lineage id not listed")
        if record["superseded_source_graph_node_id"] not in frame.changed_source_graph_node_ids:
            raise ValueError("SummaryInvalidationLedgerFrame record superseded source id not listed")
        if record["superseding_source_graph_node_id"] not in frame.active_source_graph_node_ids:
            raise ValueError("SummaryInvalidationLedgerFrame record active source id not listed")
        if record["invalidated_reason_code"] != "source_content_changed":
            raise ValueError("SummaryInvalidationLedgerFrame reason code must be source_content_changed")
        if record["validity_status"] != "invalidated_by_source_change":
            raise ValueError("SummaryInvalidationLedgerFrame validity_status is invalid")


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


def _count_observation_statuses(records: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        status = record.get("observation_status", "")
        if not status:
            continue
        counts[status] = counts.get(status, 0) + 1
    return counts


__all__ = [
    "CORE_EGO_TIME_AXIS_FRAME_SCHEMA_NAME",
    "CORE_EGO_TIME_AXIS_FRAME_SCHEMA_VERSION",
    "CORE_EGO_GUIDE_WORKER_HINT_FAILURE_TYPES",
    "CORE_EGO_GUIDE_WORKER_HINT_FRAME_SCHEMA_NAME",
    "CORE_EGO_GUIDE_WORKER_HINT_FRAME_SCHEMA_VERSION",
    "CORE_EGO_GUIDE_WORKER_HINT_STATUSES",
    "CORE_EGO_GUIDE_WORKER_PARSE_STATUSES",
    "GRAPH_ACCESS_LEDGER_CODE_GENERATOR",
    "GRAPH_ACCESS_STAGES",
    "GRAPH_MEMORY_CODE_GENERATOR",
    "GRAPH_MEMORY_EDGE_FRAME_SCHEMA_NAME",
    "GRAPH_MEMORY_EDGE_FRAME_SCHEMA_VERSION",
    "GRAPH_MEMORY_EDGE_KINDS",
    "GRAPH_MEMORY_NODE_FRAME_SCHEMA_NAME",
    "GRAPH_MEMORY_NODE_FRAME_SCHEMA_VERSION",
    "GRAPH_MEMORY_NODE_KINDS",
    "GRAPH_MEMORY_SNAPSHOT_FRAME_SCHEMA_NAME",
    "GRAPH_MEMORY_SNAPSHOT_FRAME_SCHEMA_VERSION",
    "TURN_ACTIVITY_GRAPH_LINK_ACTIVITY_KINDS",
    "TURN_ACTIVITY_GRAPH_LINK_CODE_GENERATOR",
    "TURN_ACTIVITY_GRAPH_LINK_FRAME_SCHEMA_NAME",
    "TURN_ACTIVITY_GRAPH_LINK_FRAME_SCHEMA_VERSION",
    "TURN_GRAPH_ACCESS_LEDGER_FRAME_SCHEMA_NAME",
    "TURN_GRAPH_ACCESS_LEDGER_FRAME_SCHEMA_VERSION",
    "RLOOP_GRAPH_GUIDE_PACKET_FRAME_SCHEMA_NAME",
    "RLOOP_GRAPH_GUIDE_PACKET_FRAME_SCHEMA_VERSION",
    "RLOOP_GUIDE_CODE_GENERATOR",
    "R_LOOP_MEMORY_HANDOFF_PACKET_FRAME_SCHEMA_NAME",
    "R_LOOP_MEMORY_HANDOFF_PACKET_FRAME_SCHEMA_VERSION",
    "R_LOOP_MEMORY_HANDOFF_SEMANTIC_HINT_STATUSES",
    "R_LOOP_MEMORY_HANDOFF_STATUSES",
    "SOURCE_VERSION_LINEAGE_CODE_GENERATOR",
    "SOURCE_VERSION_LINEAGE_FRAME_SCHEMA_NAME",
    "SOURCE_VERSION_LINEAGE_FRAME_SCHEMA_VERSION",
    "SOURCE_VERSION_LINEAGE_STATUSES",
    "SOURCE_OBSERVATION_LEDGER_CODE_GENERATOR",
    "SOURCE_OBSERVATION_LEDGER_FRAME_SCHEMA_NAME",
    "SOURCE_OBSERVATION_LEDGER_FRAME_SCHEMA_VERSION",
    "SOURCE_OBSERVATION_LEDGER_STATUSES",
    "SOURCE_OBSERVATION_STATUSES",
    "SUMMARY_INVALIDATION_LEDGER_CODE_GENERATOR",
    "SUMMARY_INVALIDATION_LEDGER_FRAME_SCHEMA_NAME",
    "SUMMARY_INVALIDATION_LEDGER_FRAME_SCHEMA_VERSION",
    "SUMMARY_INVALIDATION_LEDGER_STATUSES",
    "CoreEgoGuideWorkerHintFrame",
    "CoreEgoTimeAxisFrame",
    "GraphMemoryEdgeFrame",
    "GraphMemoryNodeFrame",
    "GraphMemorySnapshotFrame",
    "RLoopMemoryHandoffPacketFrame",
    "RLoopGraphGuidePacketFrame",
    "SourceObservationLedgerFrame",
    "SourceVersionLineageFrame",
    "SummaryInvalidationLedgerFrame",
    "TurnActivityGraphLinkFrame",
    "TurnGraphAccessLedgerFrame",
    "validate_core_ego_guide_worker_hint_frame",
    "validate_core_ego_time_axis_frame",
    "validate_graph_memory_edge_frame",
    "validate_graph_memory_node_frame",
    "validate_graph_memory_snapshot_frame",
    "validate_r_loop_memory_handoff_packet_frame",
    "validate_rloop_graph_guide_packet_frame",
    "validate_source_observation_ledger_frame",
    "validate_source_version_lineage_frame",
    "validate_summary_invalidation_ledger_frame",
    "validate_turn_activity_graph_link_frame",
    "validate_turn_graph_access_ledger_frame",
]
