from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory_export import (
    GRAPH_MEMORY_EXPORT_PACKET_DATA_TYPE,
)
from songryeon_core.core.graph_memory_store import (
    SONGRYEON_GRAPH_NAMESPACE,
    SONGRYEON_VESSEL_DATABASE_NAME,
    SONGRYEON_VESSEL_SERVICE_NAME,
)
from songryeon_core.core.trace_store import TraceStore


GRAPH_VESSEL_WRITE_PLAN_DATA_TYPE = "graph_vessel:write_plan"
GRAPH_VESSEL_ADAPTER_BOUNDARY_GENERATOR = "CODE:GRAPH_VESSEL_ADAPTER_BOUNDARY"
GRAPH_VESSEL_WRITE_PLAN_POLICY_ID = "GRAPH_VESSEL_WRITE_PLAN_BOUNDARY_V0"
GRAPH_VESSEL_WRITE_PLAN_SCHEMA_NAME = "GraphVesselWritePlan"
GRAPH_VESSEL_WRITE_PLAN_STATUSES = {
    "ready_to_write",
    "blocked_integrity_failed",
}
GRAPH_VESSEL_WRITE_OPERATION_KINDS = {
    "upsert_source_payload",
    "upsert_graph_node",
    "upsert_graph_edge",
    "upsert_support_record",
}


@dataclass(frozen=True)
class GraphVesselWriteOperation:
    operation_id: str
    operation_index: int
    operation_kind: str
    source_data_id: str
    source_data_type: str
    external_write_status: str = "not_run"


@dataclass(frozen=True)
class GraphVesselWritePlan:
    plan_id: str
    export_packet_id: str
    export_packet_batch_id: str
    created_at: str
    policy_id: str
    target_adapter_name: str
    vessel_database_name: str
    graph_namespace: str
    plan_status: str
    block_reason: str | None
    external_write_status: str
    operations: list[GraphVesselWriteOperation]
    operation_count: int
    operation_count_by_kind: dict[str, int]
    graph_integrity_status: str
    graph_integrity_summary: dict[str, object]
    source_data_ids: list[str]
    source_trace_ids: list[str]
    generated_by: str = GRAPH_VESSEL_ADAPTER_BOUNDARY_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = GRAPH_VESSEL_WRITE_PLAN_SCHEMA_NAME


@dataclass(frozen=True)
class RecordedGraphVesselWritePlan:
    plan: GraphVesselWritePlan
    trace_event_id: str
    created_data_ids: list[str]
    existing_data_ids: list[str]


def graph_vessel_write_plan_id(batch_id: str) -> str:
    if not batch_id:
        raise ValueError("batch_id must not be empty")
    return f"graph_vessel:write_plan:{batch_id}"


def build_graph_vessel_write_plan(
    *,
    data_store: DataStore,
    export_packet_id: str,
    created_at: str | None = None,
) -> GraphVesselWritePlan:
    """Build a no-write Vessel adapter plan from a graph memory export packet."""

    packet_record = data_store.require_record(export_packet_id)
    if packet_record.data_type != GRAPH_MEMORY_EXPORT_PACKET_DATA_TYPE:
        raise ValueError(f"expected graph memory export packet: {export_packet_id}")
    if not isinstance(packet_record.payload, dict):
        raise TypeError("graph memory export packet payload must be dict")

    packet = packet_record.payload
    batch_id = _require_str(packet, "batch_id")
    target_adapter_name = _require_str(packet, "target_adapter_name")
    if target_adapter_name != SONGRYEON_VESSEL_SERVICE_NAME:
        raise ValueError(f"unexpected target adapter name: {target_adapter_name}")

    plan_id = graph_vessel_write_plan_id(batch_id)
    timestamp = created_at or _now_iso()
    graph_integrity_status = _require_str(packet, "graph_integrity_status")
    graph_integrity_summary = _require_dict(packet, "graph_integrity_summary")
    source_trace_ids = _string_list(packet.get("source_trace_ids"))

    if graph_integrity_status != "passed":
        plan = GraphVesselWritePlan(
            plan_id=plan_id,
            export_packet_id=export_packet_id,
            export_packet_batch_id=batch_id,
            created_at=timestamp,
            policy_id=GRAPH_VESSEL_WRITE_PLAN_POLICY_ID,
            target_adapter_name=target_adapter_name,
            vessel_database_name=SONGRYEON_VESSEL_DATABASE_NAME,
            graph_namespace=SONGRYEON_GRAPH_NAMESPACE,
            plan_status="blocked_integrity_failed",
            block_reason="CODE_STATUS:graph_integrity_failed",
            external_write_status="not_run",
            operations=[],
            operation_count=0,
            operation_count_by_kind={},
            graph_integrity_status=graph_integrity_status,
            graph_integrity_summary=graph_integrity_summary,
            source_data_ids=[export_packet_id],
            source_trace_ids=source_trace_ids,
        )
        _validate_write_plan(plan)
        return plan

    operations = _build_write_operations(
        data_store=data_store,
        plan_id=plan_id,
        source_payload_data_ids=[
            *_string_list(packet.get("source_file_metadata_data_ids")),
            *_string_list(packet.get("source_text_snapshot_data_ids")),
        ],
        graph_node_data_ids=_string_list(packet.get("graph_node_data_ids")),
        graph_edge_data_ids=_string_list(packet.get("graph_edge_data_ids")),
        support_record_data_ids=[
            *_string_list(packet.get("core_ego_time_axis_frame_ids")),
            *_string_list(packet.get("graph_snapshot_data_ids")),
            *_string_list(packet.get("rloop_guide_packet_data_ids")),
            *_string_list(packet.get("source_ingest_frame_data_ids")),
            *_string_list(packet.get("source_manifest_frame_data_ids")),
            *_string_list(packet.get("source_version_lineage_frame_data_ids")),
            *_string_list(packet.get("source_observation_ledger_frame_data_ids")),
            *_string_list(packet.get("summary_invalidation_ledger_frame_data_ids")),
        ],
    )
    plan = GraphVesselWritePlan(
        plan_id=plan_id,
        export_packet_id=export_packet_id,
        export_packet_batch_id=batch_id,
        created_at=timestamp,
        policy_id=GRAPH_VESSEL_WRITE_PLAN_POLICY_ID,
        target_adapter_name=target_adapter_name,
        vessel_database_name=SONGRYEON_VESSEL_DATABASE_NAME,
        graph_namespace=SONGRYEON_GRAPH_NAMESPACE,
        plan_status="ready_to_write",
        block_reason=None,
        external_write_status="not_run",
        operations=operations,
        operation_count=len(operations),
        operation_count_by_kind=_count_operations_by_kind(operations),
        graph_integrity_status=graph_integrity_status,
        graph_integrity_summary=graph_integrity_summary,
        source_data_ids=_unique_strings(
            [export_packet_id, *[operation.source_data_id for operation in operations]]
        ),
        source_trace_ids=source_trace_ids,
    )
    _validate_write_plan(plan)
    return plan


def record_graph_vessel_write_plan(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    export_packet_id: str,
    created_at: str | None = None,
) -> RecordedGraphVesselWritePlan:
    """Record a no-write Vessel adapter plan in TraceStore/DataStore."""

    plan = build_graph_vessel_write_plan(
        data_store=data_store,
        export_packet_id=export_packet_id,
        created_at=created_at,
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="graph_vessel_adapter_boundary",
        event_type="node_output",
        timestamp=plan.created_at,
        input_ref=plan.source_trace_ids,
        output_ref=[plan.plan_id],
        schema_status="passed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=plan.plan_id,
        data_type=GRAPH_VESSEL_WRITE_PLAN_DATA_TYPE,
        payload=asdict(plan),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedGraphVesselWritePlan(
        plan=plan,
        trace_event_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def _build_write_operations(
    *,
    data_store: DataStore,
    plan_id: str,
    source_payload_data_ids: list[str],
    graph_node_data_ids: list[str],
    graph_edge_data_ids: list[str],
    support_record_data_ids: list[str],
) -> list[GraphVesselWriteOperation]:
    operations: list[GraphVesselWriteOperation] = []
    for operation_kind, data_ids in [
        ("upsert_source_payload", source_payload_data_ids),
        ("upsert_graph_node", graph_node_data_ids),
        ("upsert_graph_edge", graph_edge_data_ids),
        ("upsert_support_record", support_record_data_ids),
    ]:
        for data_id in _unique_strings(data_ids):
            record = data_store.require_record(data_id)
            operation_index = len(operations) + 1
            operation = GraphVesselWriteOperation(
                operation_id=f"{plan_id}:op:{operation_index:04d}",
                operation_index=operation_index,
                operation_kind=operation_kind,
                source_data_id=record.data_id,
                source_data_type=record.data_type,
            )
            _validate_write_operation(operation)
            operations.append(operation)
    return operations


def _validate_write_plan(plan: GraphVesselWritePlan) -> None:
    if plan.generated_by != GRAPH_VESSEL_ADAPTER_BOUNDARY_GENERATOR:
        raise ValueError("GraphVesselWritePlan.generated_by must be code boundary")
    if plan.info_class != "absolute":
        raise ValueError("GraphVesselWritePlan.info_class must be absolute")
    if plan.semantic_judgement_status != "not_run":
        raise ValueError("GraphVesselWritePlan.semantic_judgement_status must be not_run")
    if plan.external_write_status != "not_run":
        raise ValueError("GraphVesselWritePlan.external_write_status must be not_run")
    if plan.plan_status not in GRAPH_VESSEL_WRITE_PLAN_STATUSES:
        raise ValueError("GraphVesselWritePlan.plan_status is invalid")
    if plan.target_adapter_name != SONGRYEON_VESSEL_SERVICE_NAME:
        raise ValueError("GraphVesselWritePlan.target_adapter_name is invalid")
    if plan.vessel_database_name != SONGRYEON_VESSEL_DATABASE_NAME:
        raise ValueError("GraphVesselWritePlan.vessel_database_name is invalid")
    if plan.graph_namespace != SONGRYEON_GRAPH_NAMESPACE:
        raise ValueError("GraphVesselWritePlan.graph_namespace is invalid")
    if plan.plan_status == "ready_to_write" and not plan.operations:
        raise ValueError("ready_to_write plan must include operations")
    if plan.plan_status == "blocked_integrity_failed" and plan.operations:
        raise ValueError("blocked write plan must not include operations")
    if plan.operation_count != len(plan.operations):
        raise ValueError("GraphVesselWritePlan.operation_count mismatch")
    for operation in plan.operations:
        _validate_write_operation(operation)


def _validate_write_operation(operation: GraphVesselWriteOperation) -> None:
    if not operation.operation_id:
        raise ValueError("GraphVesselWriteOperation.operation_id must not be empty")
    if operation.operation_index <= 0:
        raise ValueError("GraphVesselWriteOperation.operation_index must be positive")
    if operation.operation_kind not in GRAPH_VESSEL_WRITE_OPERATION_KINDS:
        raise ValueError("GraphVesselWriteOperation.operation_kind is invalid")
    if not operation.source_data_id:
        raise ValueError("GraphVesselWriteOperation.source_data_id must not be empty")
    if not operation.source_data_type:
        raise ValueError("GraphVesselWriteOperation.source_data_type must not be empty")
    if operation.external_write_status != "not_run":
        raise ValueError("GraphVesselWriteOperation.external_write_status must be not_run")


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
            raise ValueError(f"graph vessel plan data_id collision with different type: {data_id}")
        if existing.payload != payload:
            raise ValueError(f"graph vessel plan data_id collision with different payload: {data_id}")
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


def _count_operations_by_kind(
    operations: list[GraphVesselWriteOperation],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for operation in operations:
        counts[operation.operation_kind] = counts.get(operation.operation_kind, 0) + 1
    return counts


def _require_str(payload: dict[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _require_dict(payload: dict[str, object], field_name: str) -> dict[str, object]:
    value = payload.get(field_name)
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dict")
    return value


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


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
    "GRAPH_VESSEL_ADAPTER_BOUNDARY_GENERATOR",
    "GRAPH_VESSEL_WRITE_OPERATION_KINDS",
    "GRAPH_VESSEL_WRITE_PLAN_DATA_TYPE",
    "GRAPH_VESSEL_WRITE_PLAN_POLICY_ID",
    "GRAPH_VESSEL_WRITE_PLAN_STATUSES",
    "GraphVesselWriteOperation",
    "GraphVesselWritePlan",
    "RecordedGraphVesselWritePlan",
    "build_graph_vessel_write_plan",
    "graph_vessel_write_plan_id",
    "record_graph_vessel_write_plan",
]
