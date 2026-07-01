from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from songryeon_core.core.data_store import DataRecord, DataStore
from songryeon_core.core.graph_memory_integrity import audit_graph_memory_integrity
from songryeon_core.core.trace_store import TraceStore


GRAPH_MEMORY_EXPORT_PACKET_DATA_TYPE = "graph_memory:export_packet"
GRAPH_MEMORY_EXPORT_PACKET_GENERATOR = "CODE:GRAPH_MEMORY_EXPORT_PACKET_BUILDER"
GRAPH_MEMORY_EXPORT_PACKET_POLICY_ID = "GRAPH_MEMORY_EXPORT_PACKET_V0"
GRAPH_MEMORY_EXPORT_TARGET_ADAPTER = "songryeon-neo4j-vessel"

GRAPH_MEMORY_NODE_DATA_TYPE_PREFIX = "graph_memory:node:"
GRAPH_MEMORY_EDGE_DATA_TYPE_PREFIX = "graph_memory:edge:"

_GRAPH_MEMORY_DATA_TYPES = {
    "graph_memory:core_ego_time_axis_frame",
    "graph_memory:rloop_guide_packet",
    "graph_memory:snapshot",
}
_GRAPH_SOURCE_DATA_TYPES = {
    "graph_source:file_metadata",
    "graph_source:file_text_snapshot",
    "graph_source:source_kind_ingest_frame",
    "graph_source:songryeon_core_source_manifest_frame",
}


@dataclass(frozen=True)
class GraphMemoryExportPacket:
    packet_id: str
    batch_id: str
    created_at: str
    policy_id: str
    target_adapter_name: str
    external_write_status: str
    graph_integrity_status: str
    graph_integrity_summary: dict[str, object]
    graph_node_data_ids: list[str]
    graph_edge_data_ids: list[str]
    graph_snapshot_data_ids: list[str]
    core_ego_time_axis_frame_ids: list[str]
    rloop_guide_packet_data_ids: list[str]
    source_file_metadata_data_ids: list[str]
    source_text_snapshot_data_ids: list[str]
    source_ingest_frame_data_ids: list[str]
    source_manifest_frame_data_ids: list[str]
    included_data_ids: list[str]
    source_trace_ids: list[str]
    data_type_counts: dict[str, int]
    generated_by: str = GRAPH_MEMORY_EXPORT_PACKET_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"


@dataclass(frozen=True)
class RecordedGraphMemoryExportPacket:
    packet: GraphMemoryExportPacket
    trace_event_id: str
    created_data_ids: list[str]
    existing_data_ids: list[str]


def graph_memory_export_packet_id(batch_id: str) -> str:
    if not batch_id:
        raise ValueError("batch_id must not be empty")
    return f"graph_memory:export_packet:{batch_id}"


def build_graph_memory_export_packet(
    *,
    data_store: DataStore,
    batch_id: str,
    created_at: str | None = None,
) -> GraphMemoryExportPacket:
    """Build a code-only packet that lists graph/source records ready for export."""

    timestamp = created_at or _now_iso()
    graph_node_data_ids: list[str] = []
    graph_edge_data_ids: list[str] = []
    graph_snapshot_data_ids: list[str] = []
    core_ego_time_axis_frame_ids: list[str] = []
    rloop_guide_packet_data_ids: list[str] = []
    source_file_metadata_data_ids: list[str] = []
    source_text_snapshot_data_ids: list[str] = []
    source_ingest_frame_data_ids: list[str] = []
    source_manifest_frame_data_ids: list[str] = []
    included_records: list[DataRecord] = []

    for record in data_store.list_records():
        data_type = record.data_type
        if data_type.startswith(GRAPH_MEMORY_NODE_DATA_TYPE_PREFIX):
            graph_node_data_ids.append(record.data_id)
            included_records.append(record)
        elif data_type.startswith(GRAPH_MEMORY_EDGE_DATA_TYPE_PREFIX):
            graph_edge_data_ids.append(record.data_id)
            included_records.append(record)
        elif data_type == "graph_memory:snapshot":
            graph_snapshot_data_ids.append(record.data_id)
            included_records.append(record)
        elif data_type == "graph_memory:core_ego_time_axis_frame":
            core_ego_time_axis_frame_ids.append(record.data_id)
            included_records.append(record)
        elif data_type == "graph_memory:rloop_guide_packet":
            rloop_guide_packet_data_ids.append(record.data_id)
            included_records.append(record)
        elif data_type == "graph_source:file_metadata":
            source_file_metadata_data_ids.append(record.data_id)
            included_records.append(record)
        elif data_type == "graph_source:file_text_snapshot":
            source_text_snapshot_data_ids.append(record.data_id)
            included_records.append(record)
        elif data_type == "graph_source:source_kind_ingest_frame":
            source_ingest_frame_data_ids.append(record.data_id)
            included_records.append(record)
        elif data_type == "graph_source:songryeon_core_source_manifest_frame":
            source_manifest_frame_data_ids.append(record.data_id)
            included_records.append(record)

    integrity_report = audit_graph_memory_integrity(DataStore(included_records))
    packet = GraphMemoryExportPacket(
        packet_id=graph_memory_export_packet_id(batch_id),
        batch_id=batch_id,
        created_at=timestamp,
        policy_id=GRAPH_MEMORY_EXPORT_PACKET_POLICY_ID,
        target_adapter_name=GRAPH_MEMORY_EXPORT_TARGET_ADAPTER,
        external_write_status="not_run",
        graph_integrity_status="passed" if integrity_report.passed else "failed",
        graph_integrity_summary=integrity_report.to_summary(),
        graph_node_data_ids=graph_node_data_ids,
        graph_edge_data_ids=graph_edge_data_ids,
        graph_snapshot_data_ids=graph_snapshot_data_ids,
        core_ego_time_axis_frame_ids=core_ego_time_axis_frame_ids,
        rloop_guide_packet_data_ids=rloop_guide_packet_data_ids,
        source_file_metadata_data_ids=source_file_metadata_data_ids,
        source_text_snapshot_data_ids=source_text_snapshot_data_ids,
        source_ingest_frame_data_ids=source_ingest_frame_data_ids,
        source_manifest_frame_data_ids=source_manifest_frame_data_ids,
        included_data_ids=_unique_strings([record.data_id for record in included_records]),
        source_trace_ids=_unique_strings(
            [record.source_trace_id for record in included_records]
        ),
        data_type_counts=_count_by_data_type(included_records),
    )
    _validate_export_packet(packet)
    return packet


def record_graph_memory_export_packet(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    batch_id: str,
    created_at: str | None = None,
) -> RecordedGraphMemoryExportPacket:
    """Record the export packet in DataStore without writing to any external DB."""

    packet = build_graph_memory_export_packet(
        data_store=data_store,
        batch_id=batch_id,
        created_at=created_at,
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="graph_memory_export_packet_builder",
        event_type="node_output",
        timestamp=packet.created_at,
        input_ref=packet.source_trace_ids,
        output_ref=[packet.packet_id],
        schema_status="passed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=packet.packet_id,
        data_type=GRAPH_MEMORY_EXPORT_PACKET_DATA_TYPE,
        payload=asdict(packet),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedGraphMemoryExportPacket(
        packet=packet,
        trace_event_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def _validate_export_packet(packet: GraphMemoryExportPacket) -> None:
    if packet.generated_by != GRAPH_MEMORY_EXPORT_PACKET_GENERATOR:
        raise ValueError("GraphMemoryExportPacket.generated_by must be code builder")
    if packet.info_class != "absolute":
        raise ValueError("GraphMemoryExportPacket.info_class must be absolute")
    if packet.semantic_judgement_status != "not_run":
        raise ValueError("GraphMemoryExportPacket.semantic_judgement_status must be not_run")
    if packet.external_write_status != "not_run":
        raise ValueError("GraphMemoryExportPacket.external_write_status must be not_run")
    if packet.graph_integrity_status not in {"passed", "failed"}:
        raise ValueError("GraphMemoryExportPacket.graph_integrity_status is invalid")
    if not packet.included_data_ids:
        raise ValueError("GraphMemoryExportPacket.included_data_ids must not be empty")


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
            raise ValueError(f"graph export data_id collision with different type: {data_id}")
        if existing.payload != payload:
            raise ValueError(f"graph export data_id collision with different payload: {data_id}")
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


def _count_by_data_type(records: list[DataRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record.data_type] = counts.get(record.data_type, 0) + 1
    return counts


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


__all__ = [
    "GRAPH_MEMORY_EXPORT_PACKET_DATA_TYPE",
    "GRAPH_MEMORY_EXPORT_PACKET_GENERATOR",
    "GRAPH_MEMORY_EXPORT_PACKET_POLICY_ID",
    "GRAPH_MEMORY_EXPORT_TARGET_ADAPTER",
    "GraphMemoryExportPacket",
    "RecordedGraphMemoryExportPacket",
    "build_graph_memory_export_packet",
    "graph_memory_export_packet_id",
    "record_graph_memory_export_packet",
]
