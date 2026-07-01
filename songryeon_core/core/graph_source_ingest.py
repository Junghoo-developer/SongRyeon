from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    GRAPH_MEMORY_CODE_GENERATOR,
    GraphMemoryEdgeFrame,
    GraphMemoryNodeFrame,
    validate_graph_memory_edge_frame,
    validate_graph_memory_node_frame,
)
from songryeon_core.core.trace_store import TraceStore


GRAPH_SOURCE_KINDS = {
    "internal_document",
    "source_code_file",
    "external_project_file",
}
GRAPH_SOURCE_KIND_INGEST_GENERATOR = "CODE:GRAPH_SOURCE_KIND_INGEST"
GRAPH_SOURCE_KIND_BUNDLE_POLICY_ID = "SOURCE_KIND_SEPARATED_INGEST_V0"
GRAPH_SOURCE_FILE_DATA_TYPE = "graph_source:file_metadata"
GRAPH_SOURCE_INGEST_FRAME_DATA_TYPE = "graph_source:source_kind_ingest_frame"


@dataclass(frozen=True)
class GraphSourceKindIngestResult:
    frame_id: str
    trace_event_id: str
    source_file_data_ids: list[str]
    raw_source_node_ids: list[str]
    source_kind_bundle_node_ids: list[str]
    graph_edge_ids: list[str]
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
) -> GraphSourceKindIngestResult:
    """Record source-kind-separated file coordinates as graph memory leaves."""

    if not turn_id:
        raise ValueError("turn_id must not be empty")
    if not batch_id:
        raise ValueError("batch_id must not be empty")

    prepared_by_kind = _prepare_source_files_by_kind(source_paths_by_kind)
    raw_nodes: list[GraphMemoryNodeFrame] = []
    bundle_nodes: list[GraphMemoryNodeFrame] = []
    edges: list[GraphMemoryEdgeFrame] = []
    source_file_data_ids: list[str] = []
    source_kind_counts: dict[str, int] = {}

    for source_kind in sorted(prepared_by_kind):
        prepared_files = prepared_by_kind[source_kind]
        if not prepared_files:
            continue
        source_kind_counts[source_kind] = len(prepared_files)
        source_file_data_ids.extend(
            prepared.source_file_data_id for prepared in prepared_files
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
    raw_source_node_ids = [node.node_id for node in raw_nodes]
    source_kind_bundle_node_ids = [node.node_id for node in bundle_nodes]
    graph_edge_ids = [edge.edge_id for edge in edges]

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="graph_source_kind_ingest",
        event_type="node_output",
        input_ref=input_ref or [],
        output_ref=[frame_id, *source_kind_bundle_node_ids, *raw_source_node_ids],
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

    for node in [*bundle_nodes, *raw_nodes]:
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

    frame_payload = {
        "frame_id": frame_id,
        "batch_id": batch_id,
        "source_kind_counts": source_kind_counts,
        "source_file_data_ids": source_file_data_ids,
        "raw_source_node_ids": raw_source_node_ids,
        "source_kind_bundle_node_ids": source_kind_bundle_node_ids,
        "graph_edge_ids": graph_edge_ids,
        "source_graph_node_ids": [
            *source_kind_bundle_node_ids,
            *raw_source_node_ids,
        ],
        "source_trace_ids": input_ref or [],
        "source_data_ids": [
            *source_kind_bundle_node_ids,
            *raw_source_node_ids,
            *graph_edge_ids,
            *source_file_data_ids,
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
        raw_source_node_ids=raw_source_node_ids,
        source_kind_bundle_node_ids=source_kind_bundle_node_ids,
        graph_edge_ids=graph_edge_ids,
        source_kind_counts=source_kind_counts,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def graph_source_kind_ingest_frame_id(batch_id: str) -> str:
    return f"graph_source:source_kind_ingest:{batch_id}"


def source_kind_bundle_graph_node_id(batch_id: str, source_kind: str) -> str:
    _validate_source_kind(source_kind)
    return f"graph:source_kind_bundle:{batch_id}:{source_kind}"


def source_file_data_id(
    *,
    source_kind: str,
    path: str | Path,
    content_sha1: str,
) -> str:
    return f"source_file:{source_kind}:{_source_digest(source_kind, path, content_sha1)}"


def raw_source_graph_node_id(
    *,
    source_kind: str,
    path: str | Path,
    content_sha1: str,
) -> str:
    return f"graph:raw_source:{source_kind}:{_source_digest(source_kind, path, content_sha1)}"


def _prepare_source_files_by_kind(
    source_paths_by_kind: dict[str, list[str | Path]],
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
            text = path.read_text(encoding="utf-8")
            content_sha1 = hashlib.sha1(text.encode("utf-8")).hexdigest()
            prepared_files.append(
                _PreparedSourceFile(
                    source_kind=source_kind,
                    path=normalized_path,
                    path_name=path.name,
                    suffix=path.suffix,
                    char_count=len(text),
                    content_sha1=content_sha1,
                    source_file_data_id=source_file_data_id(
                        source_kind=source_kind,
                        path=path,
                        content_sha1=content_sha1,
                    ),
                    raw_source_node_id=raw_source_graph_node_id(
                        source_kind=source_kind,
                        path=path,
                        content_sha1=content_sha1,
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
        source_graph_node_ids=[],
        source_trace_ids=[],
        source_data_ids=[prepared.source_file_data_id],
        generated_by=GRAPH_MEMORY_CODE_GENERATOR,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )


def _build_source_kind_bundle_node(
    *,
    batch_id: str,
    source_kind: str,
    raw_nodes: list[GraphMemoryNodeFrame],
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


def _source_file_payload(prepared: _PreparedSourceFile) -> dict[str, object]:
    return {
        "source_kind": prepared.source_kind,
        "path": prepared.path,
        "path_name": prepared.path_name,
        "suffix": prepared.suffix,
        "exists": True,
        "char_count": prepared.char_count,
        "content_sha1": prepared.content_sha1,
        "generated_by": GRAPH_SOURCE_KIND_INGEST_GENERATOR,
        "info_class": "absolute",
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


def _source_digest(source_kind: str, path: str | Path, content_sha1: str) -> str:
    _validate_source_kind(source_kind)
    normalized_path = Path(path).resolve().as_posix()
    digest_source = f"{source_kind}:{normalized_path}:{content_sha1}"
    return hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:16]


def _validate_source_kind(source_kind: str) -> None:
    if source_kind not in GRAPH_SOURCE_KINDS:
        raise ValueError(f"unknown graph source kind: {source_kind}")


__all__ = [
    "GRAPH_SOURCE_FILE_DATA_TYPE",
    "GRAPH_SOURCE_INGEST_FRAME_DATA_TYPE",
    "GRAPH_SOURCE_KINDS",
    "GRAPH_SOURCE_KIND_BUNDLE_POLICY_ID",
    "GRAPH_SOURCE_KIND_INGEST_GENERATOR",
    "GraphSourceKindIngestResult",
    "graph_source_kind_ingest_frame_id",
    "raw_source_graph_node_id",
    "record_graph_source_kind_ingest",
    "source_file_data_id",
    "source_kind_bundle_graph_node_id",
]
