from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable

from songryeon_core.core.data_store import DataRecord, DataStore
from songryeon_core.core.graph_memory_store import (
    SONGRYEON_GRAPH_NAMESPACE,
    SONGRYEON_VESSEL_DATABASE_NAME,
    SONGRYEON_VESSEL_SERVICE_NAME,
)
from songryeon_core.core.graph_vessel_adapter import (
    GRAPH_VESSEL_WRITE_PLAN_DATA_TYPE,
)
from songryeon_core.core.trace_store import TraceStore


GRAPH_VESSEL_NEO4J_WRITE_RESULT_DATA_TYPE = "graph_vessel:neo4j_write_result"
GRAPH_VESSEL_NEO4J_WRITER_GENERATOR = "CODE:GRAPH_VESSEL_NEO4J_WRITER"
GRAPH_VESSEL_NEO4J_WRITE_POLICY_ID = "LOCAL_VESSEL_NEO4J_FIRST_WRITE_V0"
GRAPH_VESSEL_NEO4J_WRITE_RESULT_SCHEMA_NAME = "GraphVesselNeo4jWriteResultFrame"
GRAPH_VESSEL_BASE_LABEL = "VesselRecord"
GRAPH_VESSEL_LEGACY_LABELS = (
    "SongRyeonRecord",
    "SongRyeonGraphNode",
    "SongRyeonGraphEdgeRecord",
    "SongRyeonSupportRecord",
    "SongRyeonSourcePayload",
)
GRAPH_VESSEL_LEGACY_RELATIONSHIP_TYPE = "SONGRYEON_GRAPH_EDGE"
GRAPH_VESSEL_NEO4J_WRITE_STATUSES = {
    "written",
    "adapter_unavailable",
    "blocked_plan_not_ready",
    "blocked_external_status_not_not_run",
    "blocked_integrity_failed",
    "blocked_target_adapter_mismatch",
    "write_failed",
}

Neo4jDriverFactory = Callable[..., Any]


@dataclass(frozen=True)
class GraphVesselNeo4jConfig:
    uri: str
    user: str
    password: str | None
    database: str
    allow_no_auth: bool = False


@dataclass(frozen=True)
class GraphVesselNeo4jWriteResultFrame:
    result_id: str
    plan_id: str
    created_at: str
    policy_id: str
    target_adapter_name: str
    vessel_database_name: str
    graph_namespace: str
    write_status: str
    failure_type: str | None
    failure_reason: str | None
    external_write_status: str
    attempted_operation_count: int
    written_operation_count: int
    operation_count_by_kind: dict[str, int]
    neo4j_record_node_count: int | None
    neo4j_graph_edge_count: int | None
    source_data_ids: list[str]
    source_trace_ids: list[str]
    generated_by: str = GRAPH_VESSEL_NEO4J_WRITER_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = GRAPH_VESSEL_NEO4J_WRITE_RESULT_SCHEMA_NAME


@dataclass(frozen=True)
class RecordedGraphVesselNeo4jWriteResult:
    result: GraphVesselNeo4jWriteResultFrame
    trace_event_id: str
    created_data_ids: list[str]
    existing_data_ids: list[str]


def graph_vessel_neo4j_write_result_id(plan_id: str) -> str:
    if not plan_id:
        raise ValueError("plan_id must not be empty")
    return f"graph_vessel:neo4j_write_result:{_stable_suffix(plan_id)}"


def graph_vessel_neo4j_config_from_env(
    *,
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    allow_no_auth: bool = False,
) -> GraphVesselNeo4jConfig:
    return GraphVesselNeo4jConfig(
        uri=uri
        or os.environ.get("SONGRYEON_NEO4J_URI")
        or os.environ.get("NEO4J_URI")
        or "bolt://localhost:7687",
        user=user
        or os.environ.get("SONGRYEON_NEO4J_USER")
        or os.environ.get("NEO4J_USER")
        or "neo4j",
        password=(
            password
            if password is not None
            else os.environ.get("SONGRYEON_NEO4J_PASSWORD")
            or os.environ.get("NEO4J_PASSWORD")
        ),
        database=database
        or os.environ.get("SONGRYEON_NEO4J_DATABASE")
        or os.environ.get("NEO4J_DATABASE")
        or SONGRYEON_VESSEL_DATABASE_NAME,
        allow_no_auth=allow_no_auth,
    )


def write_graph_vessel_plan_to_neo4j(
    *,
    data_store: DataStore,
    plan_id: str,
    config: GraphVesselNeo4jConfig,
    created_at: str | None = None,
    driver_factory: Neo4jDriverFactory | None = None,
) -> GraphVesselNeo4jWriteResultFrame:
    plan_record = data_store.require_record(plan_id)
    if plan_record.data_type != GRAPH_VESSEL_WRITE_PLAN_DATA_TYPE:
        raise ValueError(f"expected graph vessel write plan: {plan_id}")
    if not isinstance(plan_record.payload, dict):
        raise TypeError("graph vessel write plan payload must be dict")

    plan = plan_record.payload
    timestamp = created_at or _now_iso()
    source_trace_ids = _string_list(plan.get("source_trace_ids"))
    result_id = graph_vessel_neo4j_write_result_id(plan_id)
    base = _ResultBase(
        result_id=result_id,
        plan_id=plan_id,
        created_at=timestamp,
        target_adapter_name=_optional_str(plan.get("target_adapter_name"))
        or SONGRYEON_VESSEL_SERVICE_NAME,
        vessel_database_name=config.database,
        graph_namespace=SONGRYEON_GRAPH_NAMESPACE,
        source_data_ids=_unique_strings([plan_id, *_string_list(plan.get("source_data_ids"))]),
        source_trace_ids=source_trace_ids,
    )

    block = _plan_block_status(plan)
    if block is not None:
        status, failure_type, failure_reason = block
        return _make_result(
            base=base,
            write_status=status,
            failure_type=failure_type,
            failure_reason=failure_reason,
            attempted_operation_count=0,
            written_operation_count=0,
            operation_count_by_kind={},
            neo4j_record_node_count=None,
            neo4j_graph_edge_count=None,
        )

    if not config.uri or not config.user or not config.database:
        return _make_result(
            base=base,
            write_status="adapter_unavailable",
            failure_type="neo4j_config_missing",
            failure_reason="Neo4j uri/user/database config is incomplete.",
            attempted_operation_count=0,
            written_operation_count=0,
            operation_count_by_kind={},
            neo4j_record_node_count=None,
            neo4j_graph_edge_count=None,
        )
    if config.password is None and not config.allow_no_auth:
        return _make_result(
            base=base,
            write_status="adapter_unavailable",
            failure_type="neo4j_config_missing",
            failure_reason="Neo4j password is not configured. Set SONGRYEON_NEO4J_PASSWORD or pass --password.",
            attempted_operation_count=0,
            written_operation_count=0,
            operation_count_by_kind={},
            neo4j_record_node_count=None,
            neo4j_graph_edge_count=None,
        )

    driver_factory = driver_factory or _load_neo4j_driver_factory()
    if driver_factory is None:
        return _make_result(
            base=base,
            write_status="adapter_unavailable",
            failure_type="neo4j_driver_missing",
            failure_reason="Python neo4j package is not installed.",
            attempted_operation_count=0,
            written_operation_count=0,
            operation_count_by_kind={},
            neo4j_record_node_count=None,
            neo4j_graph_edge_count=None,
        )

    operations = _operation_dicts(plan.get("operations"))
    try:
        auth = None if config.allow_no_auth and config.password is None else (config.user, config.password)
        driver = driver_factory(config.uri, auth=auth)
        try:
            with driver.session(database=config.database) as session:
                written = 0
                for operation in operations:
                    session.execute_write(
                        _execute_write_operation,
                        data_store,
                        operation,
                        SONGRYEON_GRAPH_NAMESPACE,
                        timestamp,
                    )
                    written += 1
                record_count, edge_count = session.execute_read(
                    _read_vessel_counts,
                    SONGRYEON_GRAPH_NAMESPACE,
                )
        finally:
            close = getattr(driver, "close", None)
            if callable(close):
                close()
    except Exception as exc:
        return _make_result(
            base=base,
            write_status="write_failed",
            failure_type="neo4j_write_failed",
            failure_reason=f"{type(exc).__name__}: {exc}",
            attempted_operation_count=len(operations),
            written_operation_count=0,
            operation_count_by_kind=_count_operations_by_kind(operations),
            neo4j_record_node_count=None,
            neo4j_graph_edge_count=None,
        )

    return _make_result(
        base=base,
        write_status="written",
        failure_type=None,
        failure_reason=None,
        attempted_operation_count=len(operations),
        written_operation_count=written,
        operation_count_by_kind=_count_operations_by_kind(operations),
        neo4j_record_node_count=record_count,
        neo4j_graph_edge_count=edge_count,
    )


def record_graph_vessel_neo4j_write_result(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    plan_id: str,
    config: GraphVesselNeo4jConfig,
    created_at: str | None = None,
    driver_factory: Neo4jDriverFactory | None = None,
) -> RecordedGraphVesselNeo4jWriteResult:
    result = write_graph_vessel_plan_to_neo4j(
        data_store=data_store,
        plan_id=plan_id,
        config=config,
        created_at=created_at,
        driver_factory=driver_factory,
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="graph_vessel_neo4j_writer",
        event_type="node_output",
        timestamp=result.created_at,
        input_ref=result.source_trace_ids,
        output_ref=[result.result_id],
        schema_status="passed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=result.result_id,
        data_type=GRAPH_VESSEL_NEO4J_WRITE_RESULT_DATA_TYPE,
        payload=asdict(result),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedGraphVesselNeo4jWriteResult(
        result=result,
        trace_event_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


@dataclass(frozen=True)
class _ResultBase:
    result_id: str
    plan_id: str
    created_at: str
    target_adapter_name: str
    vessel_database_name: str
    graph_namespace: str
    source_data_ids: list[str]
    source_trace_ids: list[str]


def _make_result(
    *,
    base: _ResultBase,
    write_status: str,
    failure_type: str | None,
    failure_reason: str | None,
    attempted_operation_count: int,
    written_operation_count: int,
    operation_count_by_kind: dict[str, int],
    neo4j_record_node_count: int | None,
    neo4j_graph_edge_count: int | None,
) -> GraphVesselNeo4jWriteResultFrame:
    result = GraphVesselNeo4jWriteResultFrame(
        result_id=base.result_id,
        plan_id=base.plan_id,
        created_at=base.created_at,
        policy_id=GRAPH_VESSEL_NEO4J_WRITE_POLICY_ID,
        target_adapter_name=base.target_adapter_name,
        vessel_database_name=base.vessel_database_name,
        graph_namespace=base.graph_namespace,
        write_status=write_status,
        failure_type=failure_type,
        failure_reason=failure_reason,
        external_write_status="written" if write_status == "written" else "not_run",
        attempted_operation_count=attempted_operation_count,
        written_operation_count=written_operation_count,
        operation_count_by_kind=operation_count_by_kind,
        neo4j_record_node_count=neo4j_record_node_count,
        neo4j_graph_edge_count=neo4j_graph_edge_count,
        source_data_ids=base.source_data_ids,
        source_trace_ids=base.source_trace_ids,
    )
    _validate_write_result(result)
    return result


def _plan_block_status(
    plan: dict[str, object],
) -> tuple[str, str, str] | None:
    target_adapter_name = _optional_str(plan.get("target_adapter_name"))
    if target_adapter_name != SONGRYEON_VESSEL_SERVICE_NAME:
        return (
            "blocked_target_adapter_mismatch",
            "target_adapter_mismatch",
            f"Expected {SONGRYEON_VESSEL_SERVICE_NAME}, got {target_adapter_name}.",
        )
    if _optional_str(plan.get("plan_status")) != "ready_to_write":
        return (
            "blocked_plan_not_ready",
            "plan_status_not_ready",
            "GraphVesselWritePlan.plan_status is not ready_to_write.",
        )
    if _optional_str(plan.get("external_write_status")) != "not_run":
        return (
            "blocked_external_status_not_not_run",
            "external_write_status_not_not_run",
            "GraphVesselWritePlan.external_write_status is not not_run.",
        )
    if _optional_str(plan.get("graph_integrity_status")) != "passed":
        return (
            "blocked_integrity_failed",
            "graph_integrity_failed",
            "GraphVesselWritePlan.graph_integrity_status is not passed.",
        )
    return None


def _execute_write_operation(
    tx: object,
    data_store: DataStore,
    operation: dict[str, object],
    graph_namespace: str,
    written_at: str,
) -> None:
    operation_kind = _require_str(operation, "operation_kind")
    source_data_id = _require_str(operation, "source_data_id")
    record = data_store.require_record(source_data_id)
    if operation_kind == "upsert_source_payload":
        _upsert_record_node(
            tx,
            record=record,
            graph_namespace=graph_namespace,
            written_at=written_at,
            labels=["GraphMemorySource"],
        )
    elif operation_kind == "upsert_graph_node":
        _upsert_record_node(
            tx,
            record=record,
            graph_namespace=graph_namespace,
            written_at=written_at,
            labels=_graph_node_labels(record),
        )
    elif operation_kind == "upsert_graph_edge":
        _upsert_record_node(
            tx,
            record=record,
            graph_namespace=graph_namespace,
            written_at=written_at,
            labels=["GraphMemoryEdgeRecord"],
        )
        _upsert_graph_relationship(
            tx,
            record=record,
            graph_namespace=graph_namespace,
            written_at=written_at,
        )
    elif operation_kind == "upsert_support_record":
        _upsert_record_node(
            tx,
            record=record,
            graph_namespace=graph_namespace,
            written_at=written_at,
            labels=_support_record_labels(record),
        )
    else:
        raise ValueError(f"unknown graph vessel operation_kind: {operation_kind}")


def _upsert_record_node(
    tx: object,
    *,
    record: DataRecord,
    graph_namespace: str,
    written_at: str,
    labels: list[str],
) -> None:
    label_clause = _label_clause([GRAPH_VESSEL_BASE_LABEL, *labels])
    tx.run(
        f"""
        MERGE (n {{data_id: $data_id, graph_namespace: $graph_namespace}})
        {_legacy_label_remove_clause("n")}
        SET n += $properties
        SET n{label_clause}
        """,
        data_id=record.data_id,
        graph_namespace=graph_namespace,
        properties=_record_properties(record, graph_namespace=graph_namespace, written_at=written_at),
    )


def _upsert_graph_relationship(
    tx: object,
    *,
    record: DataRecord,
    graph_namespace: str,
    written_at: str,
) -> None:
    if not isinstance(record.payload, dict):
        raise TypeError(f"graph edge payload must be dict: {record.data_id}")
    edge_id = _require_str(record.payload, "edge_id")
    from_node_id = _require_str(record.payload, "from_node_id")
    to_node_id = _require_str(record.payload, "to_node_id")
    edge_kind = _require_str(record.payload, "edge_kind")
    relationship_type = _relationship_type(record.payload)
    tx.run(
        f"""
        OPTIONAL MATCH ()-[old:{GRAPH_VESSEL_LEGACY_RELATIONSHIP_TYPE} {{edge_id: $edge_id, graph_namespace: $graph_namespace}}]->()
        WITH collect(old) AS old_edges
        FOREACH (old_edge IN old_edges | DELETE old_edge)
        MERGE (from_node {{data_id: $from_node_id, graph_namespace: $graph_namespace}})
        MERGE (to_node {{data_id: $to_node_id, graph_namespace: $graph_namespace}})
        SET from_node:{GRAPH_VESSEL_BASE_LABEL}
        SET to_node:{GRAPH_VESSEL_BASE_LABEL}
        MERGE (from_node)-[r:{relationship_type} {{edge_id: $edge_id, graph_namespace: $graph_namespace}}]->(to_node)
        SET r += $properties
        """,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        edge_id=edge_id,
        graph_namespace=graph_namespace,
        properties={
            "edge_id": edge_id,
            "edge_kind": edge_kind,
            "display_relationship_type": relationship_type,
            "source_data_id": record.data_id,
            "source_data_type": record.data_type,
            "payload_json": _json(record.payload),
            "written_at": written_at,
            "generated_by": _payload_str(record.payload, "generated_by"),
            "info_class": _payload_str(record.payload, "info_class"),
            "semantic_judgement_status": _payload_str(
                record.payload,
                "semantic_judgement_status",
            ),
        },
    )


def _read_vessel_counts(tx: object, graph_namespace: str) -> tuple[int, int]:
    node_result = tx.run(
        """
        MATCH (n:VesselRecord {graph_namespace: $graph_namespace})
        RETURN count(n) AS count
        """,
        graph_namespace=graph_namespace,
    )
    edge_result = tx.run(
        """
        MATCH ()-[r {graph_namespace: $graph_namespace}]->()
        WHERE r.display_relationship_type IS NOT NULL
        RETURN count(r) AS count
        """,
        graph_namespace=graph_namespace,
    )
    return _single_count(node_result), _single_count(edge_result)


def _record_properties(
    record: DataRecord,
    *,
    graph_namespace: str,
    written_at: str,
) -> dict[str, object]:
    payload = record.payload if isinstance(record.payload, dict) else {}
    return _drop_none(
        {
            "data_id": record.data_id,
            "graph_namespace": graph_namespace,
            "source_data_type": record.data_type,
            "exists": record.exists,
            "created_at": record.created_at,
            "source_trace_id": record.source_trace_id,
            "payload_json": _json(record.payload),
            "payload_char_count": len(_json(record.payload)),
            "written_at": written_at,
            "display_name": _display_name(record),
            "display_kind": _display_kind(record),
            "display_label": _display_label(record),
            "generated_by": _payload_str(payload, "generated_by"),
            "info_class": _payload_str(payload, "info_class"),
            "semantic_judgement_status": _payload_str(payload, "semantic_judgement_status"),
            "node_kind": _payload_str(payload, "node_kind"),
            "data_kind": _payload_str(payload, "data_kind"),
            "edge_kind": _payload_str(payload, "edge_kind"),
            "source_bundle_kind": _payload_str(payload, "source_bundle_kind"),
            "source_data_ids_json": _json(payload.get("source_data_ids", [])),
            "source_trace_ids_json": _json(payload.get("source_trace_ids", [])),
            "source_graph_node_ids_json": _json(payload.get("source_graph_node_ids", [])),
        }
    )


def _validate_write_result(result: GraphVesselNeo4jWriteResultFrame) -> None:
    if result.generated_by != GRAPH_VESSEL_NEO4J_WRITER_GENERATOR:
        raise ValueError("GraphVesselNeo4jWriteResultFrame.generated_by must be writer")
    if result.info_class != "absolute":
        raise ValueError("GraphVesselNeo4jWriteResultFrame.info_class must be absolute")
    if result.semantic_judgement_status != "not_run":
        raise ValueError("GraphVesselNeo4jWriteResultFrame.semantic_judgement_status must be not_run")
    if result.write_status not in GRAPH_VESSEL_NEO4J_WRITE_STATUSES:
        raise ValueError("GraphVesselNeo4jWriteResultFrame.write_status is invalid")
    if result.external_write_status not in {"not_run", "written"}:
        raise ValueError("GraphVesselNeo4jWriteResultFrame.external_write_status is invalid")
    if result.write_status == "written" and result.external_write_status != "written":
        raise ValueError("written result must mark external_write_status=written")
    if result.write_status != "written" and result.external_write_status != "not_run":
        raise ValueError("non-written result must mark external_write_status=not_run")


def _graph_node_labels(record: DataRecord) -> list[str]:
    payload = record.payload if isinstance(record.payload, dict) else {}
    node_kind = _payload_str(payload, "node_kind")
    label_by_node_kind = {
        "core_ego": "CoreEgo",
        "time_axis": "TimeAxis",
        "time_bundle": "TimeBundle",
        "raw_capsule": "RawCapsule",
        "raw_source": "RawSource",
        "source_kind_bundle": "SourceKindBundle",
        "source_ingest_time_bundle": "SourceIngestBundle",
    }
    return ["GraphMemoryNode", label_by_node_kind.get(node_kind, "GraphMemoryNode")]


def _support_record_labels(record: DataRecord) -> list[str]:
    if record.data_type == "graph_memory:snapshot":
        return ["GraphMemorySnapshot"]
    if record.data_type == "graph_memory:rloop_guide_packet":
        return ["RLoopGuide"]
    return ["GraphMemoryIndex"]


def _relationship_type(payload: dict[str, object]) -> str:
    edge_kind = _require_str(payload, "edge_kind")
    from_node_id = _require_str(payload, "from_node_id")
    to_node_id = _require_str(payload, "to_node_id")
    if edge_kind == "NEXT":
        return "NEXT"
    if edge_kind == "CHILD_OF_TIME_AXIS":
        return "HAS_BUNDLE"
    if edge_kind == "CONTAINS":
        if from_node_id == "graph:core_ego:root" and to_node_id == "graph:axis:time":
            return "HAS_AXIS"
        if from_node_id.startswith("graph:time_bundle:") and to_node_id.startswith("graph:raw_capsule:"):
            return "CONTAINS_MEMORY"
        if from_node_id.startswith("graph:source_ingest_time_bundle:") and to_node_id.startswith("graph:source_kind_bundle:"):
            return "HAS_SOURCE_KIND"
        if from_node_id.startswith("graph:source_kind_bundle:") and to_node_id.startswith("graph:raw_source:"):
            return "CONTAINS_SOURCE"
        return "CONTAINS"
    return _safe_relationship_type(edge_kind)


def _display_name(record: DataRecord) -> str:
    payload = record.payload if isinstance(record.payload, dict) else {}
    node_kind = _payload_str(payload, "node_kind")
    if node_kind == "core_ego":
        return "CoreEgo"
    if node_kind == "time_axis":
        return "Time Axis"
    if node_kind == "time_bundle":
        return "Time Bundle"
    if node_kind == "raw_capsule":
        return f"Raw Capsule: {_payload_str(payload, 'source_turn_id') or record.data_id}"
    if node_kind == "raw_source":
        return f"Raw Source: {_payload_str(payload, 'data_kind') or record.data_id}"
    if record.data_type == "graph_memory:snapshot":
        return "Graph Memory Snapshot"
    if record.data_type == "graph_memory:rloop_guide_packet":
        return "R Loop Guide"
    if record.data_type == "graph_memory:core_ego_time_axis_frame":
        return "CoreEgo Time Axis Index"
    if record.data_type == "graph_source:source_version_lineage_frame":
        return "Source Version Lineage"
    if record.data_type == "graph_source:source_observation_ledger_frame":
        return "Source Observation Ledger"
    if record.data_type == "graph_source:summary_invalidation_ledger_frame":
        return "Summary Invalidation Ledger"
    if record.data_type.startswith("graph_source:"):
        return f"Graph Source: {record.data_type}"
    if record.data_type.startswith("graph_memory:edge:"):
        return f"Graph Edge Record: {_payload_str(payload, 'edge_kind') or record.data_id}"
    return record.data_id


def _display_kind(record: DataRecord) -> str:
    payload = record.payload if isinstance(record.payload, dict) else {}
    return (
        _payload_str(payload, "node_kind")
        or _payload_str(payload, "edge_kind")
        or record.data_type
    )


def _display_label(record: DataRecord) -> str:
    labels = (
        _graph_node_labels(record)
        if record.data_type.startswith("graph_memory:node:")
        else _support_record_labels(record)
        if record.data_type in {
            "graph_memory:snapshot",
            "graph_memory:rloop_guide_packet",
            "graph_memory:core_ego_time_axis_frame",
            "graph_source:source_kind_ingest_frame",
            "graph_source:songryeon_core_source_manifest_frame",
            "graph_source:source_version_lineage_frame",
            "graph_source:source_observation_ledger_frame",
            "graph_source:summary_invalidation_ledger_frame",
        }
        else ["GraphMemorySource"]
        if record.data_type.startswith("graph_source:")
        else ["GraphMemoryEdgeRecord"]
        if record.data_type.startswith("graph_memory:edge:")
        else [GRAPH_VESSEL_BASE_LABEL]
    )
    return labels[-1]


def _label_clause(labels: list[str]) -> str:
    return "".join(f":{_safe_label(label)}" for label in _unique_strings(labels))


def _legacy_label_remove_clause(variable_name: str) -> str:
    labels = "".join(f":{label}" for label in GRAPH_VESSEL_LEGACY_LABELS)
    return f"REMOVE {variable_name}{labels}"


def _safe_label(value: str) -> str:
    if not value or not value.replace("_", "").isalnum() or not value[0].isalpha():
        raise ValueError(f"unsafe Neo4j label: {value}")
    return value


def _safe_relationship_type(value: str) -> str:
    candidate = "".join(char if char.isalnum() else "_" for char in value.upper())
    while "__" in candidate:
        candidate = candidate.replace("__", "_")
    candidate = candidate.strip("_")
    if not candidate or not candidate[0].isalpha():
        raise ValueError(f"unsafe Neo4j relationship type: {value}")
    return candidate


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
            raise ValueError(f"Neo4j write result data_id collision with different type: {data_id}")
        if existing.payload != payload:
            raise ValueError(f"Neo4j write result data_id collision with different payload: {data_id}")
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


def _load_neo4j_driver_factory() -> Neo4jDriverFactory | None:
    try:
        from neo4j import GraphDatabase
    except ImportError:
        return None
    return GraphDatabase.driver


def _operation_dicts(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _count_operations_by_kind(operations: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for operation in operations:
        operation_kind = _optional_str(operation.get("operation_kind"))
        if operation_kind:
            counts[operation_kind] = counts.get(operation_kind, 0) + 1
    return counts


def _single_count(result: object) -> int:
    single = getattr(result, "single", None)
    if callable(single):
        record = single()
        if record is None:
            return 0
        try:
            return int(record["count"])
        except (KeyError, TypeError, ValueError):
            return 0
    try:
        first = next(iter(result))
        return int(first["count"])
    except (KeyError, TypeError, ValueError, StopIteration):
        return 0


def _require_str(payload: dict[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _payload_str(payload: dict[str, object], field_name: str) -> str | None:
    return _optional_str(payload.get(field_name))


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


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _drop_none(payload: dict[str, object | None]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if value is not None}


def _stable_suffix(value: str) -> str:
    return value.replace(":", "_").replace("/", "_").replace("\\", "_")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


__all__ = [
    "GRAPH_VESSEL_NEO4J_WRITE_RESULT_DATA_TYPE",
    "GRAPH_VESSEL_NEO4J_WRITE_STATUSES",
    "GRAPH_VESSEL_NEO4J_WRITER_GENERATOR",
    "GRAPH_VESSEL_NEO4J_WRITE_POLICY_ID",
    "GraphVesselNeo4jConfig",
    "GraphVesselNeo4jWriteResultFrame",
    "RecordedGraphVesselNeo4jWriteResult",
    "graph_vessel_neo4j_config_from_env",
    "graph_vessel_neo4j_write_result_id",
    "record_graph_vessel_neo4j_write_result",
    "write_graph_vessel_plan_to_neo4j",
]
