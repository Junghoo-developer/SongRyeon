from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import (
    CORE_EGO_ROOT_NODE_ID,
    TIME_AXIS_NODE_ID,
    rloop_graph_guide_packet_id,
)
from songryeon_core.core.schemas import (
    GRAPH_MEMORY_CODE_GENERATOR,
    RLOOP_GUIDE_CODE_GENERATOR,
    GraphMemoryEdgeFrame,
    GraphMemoryNodeFrame,
    GraphMemorySnapshotFrame,
    RLoopGraphGuidePacketFrame,
    validate_graph_memory_edge_frame,
    validate_graph_memory_node_frame,
    validate_graph_memory_snapshot_frame,
    validate_rloop_graph_guide_packet_frame,
)
from songryeon_core.core.trace_store import TraceStore


GRAPH_SOURCE_KINDS = {
    "internal_document",
    "source_code_file",
    "external_project_file",
}
GRAPH_SOURCE_KIND_INGEST_GENERATOR = "CODE:GRAPH_SOURCE_KIND_INGEST"
GRAPH_SOURCE_KIND_BUNDLE_POLICY_ID = "SOURCE_KIND_SEPARATED_INGEST_V0"
GRAPH_SOURCE_OBSERVATION_POLICY_ID = "SOURCE_OBSERVATION_SNAPSHOT_V0"
GRAPH_SOURCE_FILE_DATA_TYPE = "graph_source:file_metadata"
GRAPH_SOURCE_TEXT_SNAPSHOT_DATA_TYPE = "graph_source:file_text_snapshot"
GRAPH_SOURCE_INGEST_FRAME_DATA_TYPE = "graph_source:source_kind_ingest_frame"


@dataclass(frozen=True)
class GraphSourceKindIngestResult:
    frame_id: str
    trace_event_id: str
    source_file_data_ids: list[str]
    source_text_snapshot_data_ids: list[str]
    source_ingest_time_bundle_node_id: str
    raw_source_node_ids: list[str]
    source_kind_bundle_node_ids: list[str]
    graph_edge_ids: list[str]
    graph_snapshot_id: str
    rloop_graph_guide_packet_id: str
    source_kind_counts: dict[str, int]
    created_data_ids: list[str]
    existing_data_ids: list[str]


@dataclass(frozen=True)
class _PreparedSourceFile:
    source_kind: str
    path: str
    path_name: str
    suffix: str
    char_count: int
    content_sha1: str
    text: str
    text_snapshot_data_id: str | None
    observed_at: str
    ingested_at: str
    source_last_modified_at: str
    exists_at_ingest: bool
    source_file_data_id: str
    raw_source_node_id: str


def record_graph_source_kind_ingest(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    batch_id: str,
    source_paths_by_kind: dict[str, list[str | Path]],
    input_ref: list[str] | None = None,
    observed_at: str | None = None,
    ingested_at: str | None = None,
    store_text_snapshots: bool = False,
) -> GraphSourceKindIngestResult:
    """Record source-kind-separated file coordinates as graph memory leaves."""

    if not turn_id:
        raise ValueError("turn_id must not be empty")
    if not batch_id:
        raise ValueError("batch_id must not be empty")

    observation_time = observed_at or _now_iso()
    ingest_time = ingested_at or observation_time

    prepared_by_kind = _prepare_source_files_by_kind(
        source_paths_by_kind,
        observed_at=observation_time,
        ingested_at=ingest_time,
        store_text_snapshots=store_text_snapshots,
    )
    _require_core_ego_time_axis(data_store)
    raw_nodes: list[GraphMemoryNodeFrame] = []
    bundle_nodes: list[GraphMemoryNodeFrame] = []
    edges: list[GraphMemoryEdgeFrame] = []
    source_file_data_ids: list[str] = []
    source_text_snapshot_data_ids: list[str] = []
    source_kind_counts: dict[str, int] = {}

    for source_kind in sorted(prepared_by_kind):
        prepared_files = prepared_by_kind[source_kind]
        if not prepared_files:
            continue
        source_kind_counts[source_kind] = len(prepared_files)
        source_file_data_ids.extend(
            prepared.source_file_data_id for prepared in prepared_files
        )
        source_text_snapshot_data_ids.extend(
            prepared.text_snapshot_data_id
            for prepared in prepared_files
            if prepared.text_snapshot_data_id is not None
        )

        kind_raw_nodes = [
            _build_raw_source_node(prepared)
            for prepared in prepared_files
        ]
        for node in kind_raw_nodes:
            validate_graph_memory_node_frame(node)
        raw_nodes.extend(kind_raw_nodes)

        bundle_node = _build_source_kind_bundle_node(
            batch_id=batch_id,
            source_kind=source_kind,
            raw_nodes=kind_raw_nodes,
            observed_at=observation_time,
            ingested_at=ingest_time,
        )
        validate_graph_memory_node_frame(bundle_node)
        bundle_nodes.append(bundle_node)

        for raw_node in kind_raw_nodes:
            edge = _build_contains_edge(
                bundle_node=bundle_node,
                raw_node=raw_node,
            )
            validate_graph_memory_edge_frame(edge)
            edges.append(edge)

    frame_id = graph_source_kind_ingest_frame_id(batch_id)
    source_ingest_time_bundle_node = _build_source_ingest_time_bundle_node(
        batch_id=batch_id,
        source_kind_bundle_nodes=bundle_nodes,
        observed_at=observation_time,
        ingested_at=ingest_time,
    )
    validate_graph_memory_node_frame(source_ingest_time_bundle_node)
    edges.append(
        _build_time_axis_edge(
            source_ingest_time_bundle_node=source_ingest_time_bundle_node,
        )
    )
    for bundle_node in bundle_nodes:
        edges.append(
            _build_source_ingest_bundle_edge(
                source_ingest_time_bundle_node=source_ingest_time_bundle_node,
                source_kind_bundle_node=bundle_node,
            )
        )
    for edge in edges:
        validate_graph_memory_edge_frame(edge)

    raw_source_node_ids = [node.node_id for node in raw_nodes]
    source_kind_bundle_node_ids = [node.node_id for node in bundle_nodes]
    source_ingest_time_bundle_node_id = source_ingest_time_bundle_node.node_id
    graph_edge_ids = [edge.edge_id for edge in edges]
    graph_snapshot = _build_source_ingest_snapshot(
        batch_id=batch_id,
        source_ingest_time_bundle_node=source_ingest_time_bundle_node,
        source_kind_bundle_nodes=bundle_nodes,
        raw_nodes=raw_nodes,
        edges=edges,
        source_data_ids=[*source_file_data_ids, *source_text_snapshot_data_ids],
    )
    validate_graph_memory_snapshot_frame(graph_snapshot)
    guide_packet = _build_source_ingest_guide_packet(
        snapshot=graph_snapshot,
        nodes=[source_ingest_time_bundle_node, *bundle_nodes, *raw_nodes],
        source_data_ids=[
            graph_snapshot.snapshot_id,
            source_ingest_time_bundle_node_id,
            *source_kind_bundle_node_ids,
            *raw_source_node_ids,
            *graph_edge_ids,
            *source_file_data_ids,
            *source_text_snapshot_data_ids,
        ],
    )
    validate_rloop_graph_guide_packet_frame(guide_packet)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="graph_source_kind_ingest",
        event_type="node_output",
        timestamp=ingest_time,
        input_ref=input_ref or [],
        output_ref=[
            frame_id,
            graph_snapshot.snapshot_id,
            guide_packet.packet_id,
            source_ingest_time_bundle_node_id,
            *source_kind_bundle_node_ids,
            *raw_source_node_ids,
        ],
        schema_status="passed",
    )

    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    timestamp = event.timestamp

    for prepared in [
        prepared
        for prepared_files in prepared_by_kind.values()
        for prepared in prepared_files
    ]:
        _record_payload_if_missing(
            data_store=data_store,
            data_id=prepared.source_file_data_id,
            data_type=GRAPH_SOURCE_FILE_DATA_TYPE,
            payload=_source_file_payload(prepared),
            created_at=timestamp,
            source_trace_id=event.event_id,
            created_data_ids=created_data_ids,
            existing_data_ids=existing_data_ids,
        )
        if prepared.text_snapshot_data_id is not None:
            _record_payload_if_missing(
                data_store=data_store,
                data_id=prepared.text_snapshot_data_id,
                data_type=GRAPH_SOURCE_TEXT_SNAPSHOT_DATA_TYPE,
                payload=_source_text_snapshot_payload(prepared),
                created_at=timestamp,
                source_trace_id=event.event_id,
                created_data_ids=created_data_ids,
                existing_data_ids=existing_data_ids,
            )

    for node in [source_ingest_time_bundle_node, *bundle_nodes, *raw_nodes]:
        _record_payload_if_missing(
            data_store=data_store,
            data_id=node.node_id,
            data_type=f"graph_memory:node:{node.node_kind}",
            payload=asdict(node),
            created_at=timestamp,
            source_trace_id=event.event_id,
            created_data_ids=created_data_ids,
            existing_data_ids=existing_data_ids,
        )

    for edge in edges:
        _record_payload_if_missing(
            data_store=data_store,
            data_id=edge.edge_id,
            data_type=f"graph_memory:edge:{edge.edge_kind}",
            payload=asdict(edge),
            created_at=timestamp,
            source_trace_id=event.event_id,
            created_data_ids=created_data_ids,
            existing_data_ids=existing_data_ids,
        )

    _record_payload_if_missing(
        data_store=data_store,
        data_id=graph_snapshot.snapshot_id,
        data_type="graph_memory:snapshot",
        payload=asdict(graph_snapshot),
        created_at=timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    _record_payload_if_missing(
        data_store=data_store,
        data_id=guide_packet.packet_id,
        data_type="graph_memory:rloop_guide_packet",
        payload=asdict(guide_packet),
        created_at=timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )

    frame_payload = {
        "frame_id": frame_id,
        "batch_id": batch_id,
        "observed_at": observation_time,
        "ingested_at": ingest_time,
        "core_ego_time_axis_link_status": "linked",
        "source_ingest_time_bundle_node_id": source_ingest_time_bundle_node_id,
        "graph_snapshot_id": graph_snapshot.snapshot_id,
        "rloop_graph_guide_packet_id": guide_packet.packet_id,
        "source_kind_counts": source_kind_counts,
        "source_file_data_ids": source_file_data_ids,
        "source_text_snapshot_data_ids": source_text_snapshot_data_ids,
        "text_snapshot_status": "stored" if store_text_snapshots else "not_stored",
        "raw_source_node_ids": raw_source_node_ids,
        "source_kind_bundle_node_ids": source_kind_bundle_node_ids,
        "graph_edge_ids": graph_edge_ids,
        "source_graph_node_ids": [
            source_ingest_time_bundle_node_id,
            *source_kind_bundle_node_ids,
            *raw_source_node_ids,
        ],
        "source_trace_ids": input_ref or [],
        "source_data_ids": [
            *source_kind_bundle_node_ids,
            *raw_source_node_ids,
            *graph_edge_ids,
            *source_file_data_ids,
            *source_text_snapshot_data_ids,
        ],
        "generated_by": GRAPH_SOURCE_KIND_INGEST_GENERATOR,
        "info_class": "absolute",
        "semantic_judgement_status": "not_run",
    }
    _record_payload_if_missing(
        data_store=data_store,
        data_id=frame_id,
        data_type=GRAPH_SOURCE_INGEST_FRAME_DATA_TYPE,
        payload=frame_payload,
        created_at=timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )

    return GraphSourceKindIngestResult(
        frame_id=frame_id,
        trace_event_id=event.event_id,
        source_file_data_ids=source_file_data_ids,
        source_text_snapshot_data_ids=source_text_snapshot_data_ids,
        source_ingest_time_bundle_node_id=source_ingest_time_bundle_node_id,
        raw_source_node_ids=raw_source_node_ids,
        source_kind_bundle_node_ids=source_kind_bundle_node_ids,
        graph_edge_ids=graph_edge_ids,
        graph_snapshot_id=graph_snapshot.snapshot_id,
        rloop_graph_guide_packet_id=guide_packet.packet_id,
        source_kind_counts=source_kind_counts,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def graph_source_kind_ingest_frame_id(batch_id: str) -> str:
    return f"graph_source:source_kind_ingest:{batch_id}"


def graph_source_ingest_snapshot_id(batch_id: str) -> str:
    return f"graph:snapshot:{batch_id}:source_ingest"


def source_ingest_time_bundle_graph_node_id(batch_id: str) -> str:
    return f"graph:source_ingest_time_bundle:{batch_id}"


def source_kind_bundle_graph_node_id(batch_id: str, source_kind: str) -> str:
    _validate_source_kind(source_kind)
    return f"graph:source_kind_bundle:{batch_id}:{source_kind}"


def source_file_data_id(
    *,
    source_kind: str,
    path: str | Path,
    content_sha1: str,
    observed_at: str,
) -> str:
    return f"source_file:{source_kind}:{_source_digest(source_kind, path, content_sha1, observed_at)}"


def source_text_snapshot_data_id(
    *,
    source_kind: str,
    path: str | Path,
    content_sha1: str,
    observed_at: str,
) -> str:
    return f"source_text:{source_kind}:{_source_digest(source_kind, path, content_sha1, observed_at)}"


def raw_source_graph_node_id(
    *,
    source_kind: str,
    path: str | Path,
    content_sha1: str,
    observed_at: str,
) -> str:
    return f"graph:raw_source:{source_kind}:{_source_digest(source_kind, path, content_sha1, observed_at)}"


def _prepare_source_files_by_kind(
    source_paths_by_kind: dict[str, list[str | Path]],
    *,
    observed_at: str,
    ingested_at: str,
    store_text_snapshots: bool,
) -> dict[str, list[_PreparedSourceFile]]:
    prepared_by_kind: dict[str, list[_PreparedSourceFile]] = {}
    for source_kind, paths in source_paths_by_kind.items():
        _validate_source_kind(source_kind)
        prepared_files: list[_PreparedSourceFile] = []
        seen_paths: set[str] = set()
        for raw_path in paths:
            path = Path(raw_path).resolve()
            normalized_path = path.as_posix()
            if normalized_path in seen_paths:
                continue
            seen_paths.add(normalized_path)
            if not path.exists():
                raise FileNotFoundError(normalized_path)
            if not path.is_file():
                raise ValueError(f"source path must be a file: {normalized_path}")
            source_last_modified_at = datetime.fromtimestamp(
                path.stat().st_mtime
            ).isoformat(timespec="seconds")
            text = path.read_text(encoding="utf-8")
            content_sha1 = hashlib.sha1(text.encode("utf-8")).hexdigest()
            text_snapshot_id = (
                source_text_snapshot_data_id(
                    source_kind=source_kind,
                    path=path,
                    content_sha1=content_sha1,
                    observed_at=observed_at,
                )
                if store_text_snapshots
                else None
            )
            prepared_files.append(
                _PreparedSourceFile(
                    source_kind=source_kind,
                    path=normalized_path,
                    path_name=path.name,
                    suffix=path.suffix,
                    char_count=len(text),
                    content_sha1=content_sha1,
                    text=text,
                    text_snapshot_data_id=text_snapshot_id,
                    observed_at=observed_at,
                    ingested_at=ingested_at,
                    source_last_modified_at=source_last_modified_at,
                    exists_at_ingest=True,
                    source_file_data_id=source_file_data_id(
                        source_kind=source_kind,
                        path=path,
                        content_sha1=content_sha1,
                        observed_at=observed_at,
                    ),
                    raw_source_node_id=raw_source_graph_node_id(
                        source_kind=source_kind,
                        path=path,
                        content_sha1=content_sha1,
                        observed_at=observed_at,
                    ),
                )
            )
        prepared_by_kind[source_kind] = prepared_files
    return prepared_by_kind


def _build_raw_source_node(prepared: _PreparedSourceFile) -> GraphMemoryNodeFrame:
    return GraphMemoryNodeFrame(
        node_id=prepared.raw_source_node_id,
        node_kind="raw_source",
        data_kind=prepared.source_kind,
        summary_depth=0,
        source_depth_min=0,
        source_depth_max=0,
        source_leaf_count=1,
        source_summary_count=0,
        source_bundle_kind=prepared.source_kind,
        bundle_policy_id=GRAPH_SOURCE_KIND_BUNDLE_POLICY_ID,
        source_char_count=prepared.char_count,
        observed_at=prepared.observed_at,
        ingested_at=prepared.ingested_at,
        source_last_modified_at=prepared.source_last_modified_at,
        exists_at_ingest=prepared.exists_at_ingest,
        content_sha1=prepared.content_sha1,
        source_graph_node_ids=[],
        source_trace_ids=[],
        source_data_ids=_unique_strings(
            [
                prepared.source_file_data_id,
                prepared.text_snapshot_data_id,
            ]
        ),
        generated_by=GRAPH_MEMORY_CODE_GENERATOR,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )


def _build_source_kind_bundle_node(
    *,
    batch_id: str,
    source_kind: str,
    raw_nodes: list[GraphMemoryNodeFrame],
    observed_at: str,
    ingested_at: str,
) -> GraphMemoryNodeFrame:
    return GraphMemoryNodeFrame(
        node_id=source_kind_bundle_graph_node_id(batch_id, source_kind),
        node_kind="source_kind_bundle",
        data_kind=f"{source_kind}_bundle",
        summary_depth=0,
        source_depth_min=0,
        source_depth_max=0,
        source_leaf_count=len(raw_nodes),
        source_summary_count=0,
        source_bundle_kind=source_kind,
        bundle_policy_id=GRAPH_SOURCE_KIND_BUNDLE_POLICY_ID,
        source_char_count=sum(node.source_char_count for node in raw_nodes),
        observed_at=observed_at,
        ingested_at=ingested_at,
        source_graph_node_ids=[node.node_id for node in raw_nodes],
        source_trace_ids=[],
        source_data_ids=[
            source_data_id
            for node in raw_nodes
            for source_data_id in node.source_data_ids
        ],
        generated_by=GRAPH_MEMORY_CODE_GENERATOR,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )


def _build_source_ingest_time_bundle_node(
    *,
    batch_id: str,
    source_kind_bundle_nodes: list[GraphMemoryNodeFrame],
    observed_at: str,
    ingested_at: str,
) -> GraphMemoryNodeFrame:
    return GraphMemoryNodeFrame(
        node_id=source_ingest_time_bundle_graph_node_id(batch_id),
        node_kind="source_ingest_time_bundle",
        data_kind="source_ingest_time_bundle",
        summary_depth=0,
        source_depth_min=0,
        source_depth_max=0,
        source_leaf_count=sum(node.source_leaf_count for node in source_kind_bundle_nodes),
        source_summary_count=0,
        source_bundle_kind="source_ingest_time_bundle",
        bundle_policy_id=GRAPH_SOURCE_KIND_BUNDLE_POLICY_ID,
        source_char_count=sum(node.source_char_count for node in source_kind_bundle_nodes),
        observed_at=observed_at,
        ingested_at=ingested_at,
        source_graph_node_ids=[node.node_id for node in source_kind_bundle_nodes],
        source_trace_ids=[],
        source_data_ids=[
            source_data_id
            for node in source_kind_bundle_nodes
            for source_data_id in node.source_data_ids
        ],
        generated_by=GRAPH_MEMORY_CODE_GENERATOR,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )


def _build_contains_edge(
    *,
    bundle_node: GraphMemoryNodeFrame,
    raw_node: GraphMemoryNodeFrame,
) -> GraphMemoryEdgeFrame:
    return GraphMemoryEdgeFrame(
        edge_id=f"graph:edge:contains:{bundle_node.node_id}:{raw_node.node_id}",
        edge_kind="CONTAINS",
        from_node_id=bundle_node.node_id,
        to_node_id=raw_node.node_id,
        source_graph_node_ids=[bundle_node.node_id, raw_node.node_id],
        source_trace_ids=[],
        source_data_ids=[
            bundle_node.node_id,
            raw_node.node_id,
            *raw_node.source_data_ids,
        ],
        generated_by=GRAPH_MEMORY_CODE_GENERATOR,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )


def _build_time_axis_edge(
    *,
    source_ingest_time_bundle_node: GraphMemoryNodeFrame,
) -> GraphMemoryEdgeFrame:
    return GraphMemoryEdgeFrame(
        edge_id=(
            f"graph:edge:child_of_time_axis:"
            f"{TIME_AXIS_NODE_ID}:{source_ingest_time_bundle_node.node_id}"
        ),
        edge_kind="CHILD_OF_TIME_AXIS",
        from_node_id=TIME_AXIS_NODE_ID,
        to_node_id=source_ingest_time_bundle_node.node_id,
        source_graph_node_ids=[
            TIME_AXIS_NODE_ID,
            source_ingest_time_bundle_node.node_id,
        ],
        source_trace_ids=[],
        source_data_ids=[
            TIME_AXIS_NODE_ID,
            source_ingest_time_bundle_node.node_id,
        ],
        generated_by=GRAPH_MEMORY_CODE_GENERATOR,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )


def _build_source_ingest_bundle_edge(
    *,
    source_ingest_time_bundle_node: GraphMemoryNodeFrame,
    source_kind_bundle_node: GraphMemoryNodeFrame,
) -> GraphMemoryEdgeFrame:
    return GraphMemoryEdgeFrame(
        edge_id=(
            f"graph:edge:contains:"
            f"{source_ingest_time_bundle_node.node_id}:{source_kind_bundle_node.node_id}"
        ),
        edge_kind="CONTAINS",
        from_node_id=source_ingest_time_bundle_node.node_id,
        to_node_id=source_kind_bundle_node.node_id,
        source_graph_node_ids=[
            source_ingest_time_bundle_node.node_id,
            source_kind_bundle_node.node_id,
        ],
        source_trace_ids=[],
        source_data_ids=[
            source_ingest_time_bundle_node.node_id,
            source_kind_bundle_node.node_id,
            *source_kind_bundle_node.source_data_ids,
        ],
        generated_by=GRAPH_MEMORY_CODE_GENERATOR,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )


def _build_source_ingest_snapshot(
    *,
    batch_id: str,
    source_ingest_time_bundle_node: GraphMemoryNodeFrame,
    source_kind_bundle_nodes: list[GraphMemoryNodeFrame],
    raw_nodes: list[GraphMemoryNodeFrame],
    edges: list[GraphMemoryEdgeFrame],
    source_data_ids: list[str],
) -> GraphMemorySnapshotFrame:
    graph_node_ids = [
        CORE_EGO_ROOT_NODE_ID,
        TIME_AXIS_NODE_ID,
        source_ingest_time_bundle_node.node_id,
        *[node.node_id for node in source_kind_bundle_nodes],
        *[node.node_id for node in raw_nodes],
    ]
    graph_edge_ids = [edge.edge_id for edge in edges]
    nodes_for_counts = [
        source_ingest_time_bundle_node,
        *source_kind_bundle_nodes,
        *raw_nodes,
    ]
    node_kind_counts = _count_by_node_kind(nodes_for_counts)
    node_kind_counts["core_ego"] = 1
    node_kind_counts["time_axis"] = 1
    data_kind_counts = _count_by_data_kind(nodes_for_counts)
    data_kind_counts["core_ego_root"] = 1
    data_kind_counts["time_axis"] = 1
    return GraphMemorySnapshotFrame(
        snapshot_id=graph_source_ingest_snapshot_id(batch_id),
        batch_id=batch_id,
        root_node_id=CORE_EGO_ROOT_NODE_ID,
        time_axis_node_id=TIME_AXIS_NODE_ID,
        graph_node_ids=graph_node_ids,
        graph_edge_ids=graph_edge_ids,
        node_kind_counts=node_kind_counts,
        edge_kind_counts=_count_edges_by_kind(edges),
        data_kind_counts=data_kind_counts,
        source_graph_node_ids=graph_node_ids,
        source_trace_ids=[],
        source_data_ids=_unique_strings(
            [
                *graph_node_ids,
                *graph_edge_ids,
                *source_data_ids,
            ]
        ),
        generated_by=GRAPH_MEMORY_CODE_GENERATOR,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )


def _build_source_ingest_guide_packet(
    *,
    snapshot: GraphMemorySnapshotFrame,
    nodes: list[GraphMemoryNodeFrame],
    source_data_ids: list[str],
) -> RLoopGraphGuidePacketFrame:
    summary_depths = [node.summary_depth for node in nodes]
    source_leaf_counts = [node.source_leaf_count for node in nodes]
    return RLoopGraphGuidePacketFrame(
        packet_id=rloop_graph_guide_packet_id(snapshot.snapshot_id),
        graph_snapshot_id=snapshot.snapshot_id,
        target_consumer="R_LOOP",
        available_entry_nodes=[TIME_AXIS_NODE_ID],
        node_kind_counts=dict(snapshot.node_kind_counts),
        data_kind_counts=dict(snapshot.data_kind_counts),
        summary_depth_range=_int_range(summary_depths),
        source_leaf_count_range=_int_range(source_leaf_counts),
        risky_or_unreviewed_node_ids=[],
        recommended_traversal_hints=[],
        recommended_traversal_hints_status="not_run",
        source_graph_node_ids=list(snapshot.graph_node_ids),
        source_trace_ids=[],
        source_data_ids=_unique_strings(source_data_ids),
        generated_by=RLOOP_GUIDE_CODE_GENERATOR,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )


def _source_file_payload(prepared: _PreparedSourceFile) -> dict[str, object]:
    return {
        "source_kind": prepared.source_kind,
        "path": prepared.path,
        "path_name": prepared.path_name,
        "suffix": prepared.suffix,
        "exists": True,
        "exists_at_ingest": prepared.exists_at_ingest,
        "char_count": prepared.char_count,
        "observed_at": prepared.observed_at,
        "ingested_at": prepared.ingested_at,
        "source_last_modified_at": prepared.source_last_modified_at,
        "content_sha1": prepared.content_sha1,
        "generated_by": GRAPH_SOURCE_KIND_INGEST_GENERATOR,
        "info_class": "absolute",
        "semantic_judgement_status": "not_run",
    }


def _source_text_snapshot_payload(prepared: _PreparedSourceFile) -> dict[str, object]:
    return {
        "source_kind": prepared.source_kind,
        "path": prepared.path,
        "observed_at": prepared.observed_at,
        "ingested_at": prepared.ingested_at,
        "content_sha1": prepared.content_sha1,
        "char_count": prepared.char_count,
        "text": prepared.text,
        "generated_by": GRAPH_SOURCE_KIND_INGEST_GENERATOR,
        "info_class": "absolute_copied_source",
        "semantic_judgement_status": "not_run",
    }


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
            raise ValueError(f"graph source data_id collision with different type: {data_id}")
        if existing.payload != payload:
            raise ValueError(f"graph source data_id collision with different payload: {data_id}")
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


def _source_digest(
    source_kind: str,
    path: str | Path,
    content_sha1: str,
    observed_at: str,
) -> str:
    _validate_source_kind(source_kind)
    normalized_path = Path(path).resolve().as_posix()
    digest_source = f"{source_kind}:{normalized_path}:{content_sha1}:{observed_at}"
    return hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:16]


def _require_core_ego_time_axis(data_store: DataStore) -> None:
    missing = [
        data_id
        for data_id in (CORE_EGO_ROOT_NODE_ID, TIME_AXIS_NODE_ID)
        if data_store.get_record(data_id) is None
    ]
    if missing:
        raise ValueError(
            "source ingest requires existing CoreEgo time axis graph records: "
            + ", ".join(missing)
        )


def _count_by_node_kind(nodes: list[GraphMemoryNodeFrame]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in nodes:
        counts[node.node_kind] = counts.get(node.node_kind, 0) + 1
    return counts


def _count_by_data_kind(nodes: list[GraphMemoryNodeFrame]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in nodes:
        counts[node.data_kind] = counts.get(node.data_kind, 0) + 1
    return counts


def _count_edges_by_kind(edges: list[GraphMemoryEdgeFrame]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for edge in edges:
        counts[edge.edge_kind] = counts.get(edge.edge_kind, 0) + 1
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


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _validate_source_kind(source_kind: str) -> None:
    if source_kind not in GRAPH_SOURCE_KINDS:
        raise ValueError(f"unknown graph source kind: {source_kind}")


__all__ = [
    "GRAPH_SOURCE_FILE_DATA_TYPE",
    "GRAPH_SOURCE_INGEST_FRAME_DATA_TYPE",
    "GRAPH_SOURCE_KINDS",
    "GRAPH_SOURCE_KIND_BUNDLE_POLICY_ID",
    "GRAPH_SOURCE_KIND_INGEST_GENERATOR",
    "GRAPH_SOURCE_OBSERVATION_POLICY_ID",
    "GRAPH_SOURCE_TEXT_SNAPSHOT_DATA_TYPE",
    "GraphSourceKindIngestResult",
    "graph_source_ingest_snapshot_id",
    "graph_source_kind_ingest_frame_id",
    "raw_source_graph_node_id",
    "record_graph_source_kind_ingest",
    "source_file_data_id",
    "source_ingest_time_bundle_graph_node_id",
    "source_kind_bundle_graph_node_id",
    "source_text_snapshot_data_id",
]
