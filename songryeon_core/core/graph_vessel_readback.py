from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory_store import (
    SONGRYEON_GRAPH_NAMESPACE,
    SONGRYEON_VESSEL_SERVICE_NAME,
)
from songryeon_core.core.graph_vessel_neo4j import (
    GRAPH_VESSEL_BASE_LABEL,
    GraphVesselNeo4jConfig,
)
from songryeon_core.core.trace_store import TraceStore


GRAPH_VESSEL_NEO4J_READBACK_RESULT_DATA_TYPE = "graph_vessel:neo4j_readback_result"
GRAPH_VESSEL_NEO4J_READBACK_GENERATOR = "CODE:GRAPH_VESSEL_NEO4J_READBACK_VERIFIER"
GRAPH_VESSEL_NEO4J_READBACK_POLICY_ID = "VESSEL_READBACK_VERIFICATION_V0"
GRAPH_VESSEL_NEO4J_READBACK_SCHEMA_NAME = "GraphVesselNeo4jReadbackResultFrame"
GRAPH_VESSEL_NEO4J_READBACK_STATUSES = {
    "passed",
    "failed",
    "adapter_unavailable",
    "read_failed",
}

Neo4jDriverFactory = Callable[..., Any]


@dataclass(frozen=True)
class GraphVesselNeo4jReadbackResultFrame:
    result_id: str
    created_at: str
    policy_id: str
    target_adapter_name: str
    vessel_database_name: str
    graph_namespace: str
    readback_status: str
    failure_type: str | None
    failure_reason: str | None
    core_path_exists: bool
    core_path_count: int | None
    vessel_record_count: int | None
    vessel_relationship_count: int | None
    core_ego_count: int | None
    time_axis_count: int | None
    time_bundle_count: int | None
    raw_capsule_count: int | None
    has_axis_count: int | None
    has_bundle_count: int | None
    contains_memory_count: int | None
    required_property_missing_count: int | None
    required_property_missing_samples: list[str]
    source_data_ids: list[str]
    source_trace_ids: list[str]
    generated_by: str = GRAPH_VESSEL_NEO4J_READBACK_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = GRAPH_VESSEL_NEO4J_READBACK_SCHEMA_NAME


@dataclass(frozen=True)
class RecordedGraphVesselNeo4jReadbackResult:
    result: GraphVesselNeo4jReadbackResultFrame
    trace_event_id: str
    created_data_ids: list[str]
    existing_data_ids: list[str]


def graph_vessel_neo4j_readback_result_id(batch_id: str) -> str:
    if not batch_id:
        raise ValueError("batch_id must not be empty")
    return f"graph_vessel:neo4j_readback_result:{_stable_suffix(batch_id)}"


def readback_graph_vessel_from_neo4j(
    *,
    config: GraphVesselNeo4jConfig,
    batch_id: str = "manual_vessel_readback",
    created_at: str | None = None,
    driver_factory: Neo4jDriverFactory | None = None,
) -> GraphVesselNeo4jReadbackResultFrame:
    timestamp = created_at or _now_iso()
    base = _ReadbackBase(
        result_id=graph_vessel_neo4j_readback_result_id(batch_id),
        created_at=timestamp,
        target_adapter_name=SONGRYEON_VESSEL_SERVICE_NAME,
        vessel_database_name=config.database,
        graph_namespace=SONGRYEON_GRAPH_NAMESPACE,
    )

    config_failure = _config_failure(config)
    if config_failure is not None:
        failure_type, failure_reason = config_failure
        return _make_result(
            base=base,
            readback_status="adapter_unavailable",
            failure_type=failure_type,
            failure_reason=failure_reason,
            checks=_empty_checks(),
        )

    driver_factory = driver_factory or _load_neo4j_driver_factory()
    if driver_factory is None:
        return _make_result(
            base=base,
            readback_status="adapter_unavailable",
            failure_type="neo4j_driver_missing",
            failure_reason="Python neo4j package is not installed.",
            checks=_empty_checks(),
        )

    try:
        auth = None if config.allow_no_auth and config.password is None else (config.user, config.password)
        driver = driver_factory(config.uri, auth=auth)
        try:
            with driver.session(database=config.database) as session:
                checks = session.execute_read(_execute_readback_checks, SONGRYEON_GRAPH_NAMESPACE)
        finally:
            close = getattr(driver, "close", None)
            if callable(close):
                close()
    except Exception as exc:
        return _make_result(
            base=base,
            readback_status="read_failed",
            failure_type="neo4j_read_failed",
            failure_reason=f"{type(exc).__name__}: {exc}",
            checks=_empty_checks(),
        )

    failure_reason = _readback_failure_reason(checks)
    return _make_result(
        base=base,
        readback_status="passed" if failure_reason is None else "failed",
        failure_type=None if failure_reason is None else "readback_check_failed",
        failure_reason=failure_reason,
        checks=checks,
    )


def record_graph_vessel_neo4j_readback_result(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    config: GraphVesselNeo4jConfig,
    batch_id: str = "manual_vessel_readback",
    created_at: str | None = None,
    driver_factory: Neo4jDriverFactory | None = None,
) -> RecordedGraphVesselNeo4jReadbackResult:
    result = readback_graph_vessel_from_neo4j(
        config=config,
        batch_id=batch_id,
        created_at=created_at,
        driver_factory=driver_factory,
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="graph_vessel_neo4j_readback",
        event_type="node_output",
        timestamp=result.created_at,
        input_ref=[],
        output_ref=[result.result_id],
        schema_status="passed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=result.result_id,
        data_type=GRAPH_VESSEL_NEO4J_READBACK_RESULT_DATA_TYPE,
        payload=asdict(result),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedGraphVesselNeo4jReadbackResult(
        result=result,
        trace_event_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


@dataclass(frozen=True)
class _ReadbackBase:
    result_id: str
    created_at: str
    target_adapter_name: str
    vessel_database_name: str
    graph_namespace: str


@dataclass(frozen=True)
class _ReadbackChecks:
    core_path_count: int | None
    vessel_record_count: int | None
    vessel_relationship_count: int | None
    core_ego_count: int | None
    time_axis_count: int | None
    time_bundle_count: int | None
    raw_capsule_count: int | None
    has_axis_count: int | None
    has_bundle_count: int | None
    contains_memory_count: int | None
    required_property_missing_count: int | None
    required_property_missing_samples: list[str]


def _make_result(
    *,
    base: _ReadbackBase,
    readback_status: str,
    failure_type: str | None,
    failure_reason: str | None,
    checks: _ReadbackChecks,
) -> GraphVesselNeo4jReadbackResultFrame:
    result = GraphVesselNeo4jReadbackResultFrame(
        result_id=base.result_id,
        created_at=base.created_at,
        policy_id=GRAPH_VESSEL_NEO4J_READBACK_POLICY_ID,
        target_adapter_name=base.target_adapter_name,
        vessel_database_name=base.vessel_database_name,
        graph_namespace=base.graph_namespace,
        readback_status=readback_status,
        failure_type=failure_type,
        failure_reason=failure_reason,
        core_path_exists=(checks.core_path_count or 0) > 0,
        core_path_count=checks.core_path_count,
        vessel_record_count=checks.vessel_record_count,
        vessel_relationship_count=checks.vessel_relationship_count,
        core_ego_count=checks.core_ego_count,
        time_axis_count=checks.time_axis_count,
        time_bundle_count=checks.time_bundle_count,
        raw_capsule_count=checks.raw_capsule_count,
        has_axis_count=checks.has_axis_count,
        has_bundle_count=checks.has_bundle_count,
        contains_memory_count=checks.contains_memory_count,
        required_property_missing_count=checks.required_property_missing_count,
        required_property_missing_samples=checks.required_property_missing_samples,
        source_data_ids=[],
        source_trace_ids=[],
    )
    _validate_readback_result(result)
    return result


def _execute_readback_checks(tx: object, graph_namespace: str) -> _ReadbackChecks:
    return _ReadbackChecks(
        core_path_count=_count_core_path(tx, graph_namespace),
        vessel_record_count=_count_label(tx, graph_namespace, GRAPH_VESSEL_BASE_LABEL),
        vessel_relationship_count=_count_vessel_relationships(tx, graph_namespace),
        core_ego_count=_count_label(tx, graph_namespace, "CoreEgo"),
        time_axis_count=_count_label(tx, graph_namespace, "TimeAxis"),
        time_bundle_count=_count_label(tx, graph_namespace, "TimeBundle"),
        raw_capsule_count=_count_label(tx, graph_namespace, "RawCapsule"),
        has_axis_count=_count_relationship(tx, graph_namespace, "HAS_AXIS"),
        has_bundle_count=_count_relationship(tx, graph_namespace, "HAS_BUNDLE"),
        contains_memory_count=_count_relationship(tx, graph_namespace, "CONTAINS_MEMORY"),
        required_property_missing_count=_required_property_missing_count(tx, graph_namespace),
        required_property_missing_samples=_required_property_missing_samples(tx, graph_namespace),
    )


def _count_core_path(tx: object, graph_namespace: str) -> int:
    result = tx.run(
        """
        MATCH (:CoreEgo {graph_namespace: $graph_namespace})
          -[:HAS_AXIS {graph_namespace: $graph_namespace}]->
          (:TimeAxis {graph_namespace: $graph_namespace})
          -[:HAS_BUNDLE {graph_namespace: $graph_namespace}]->
          (:TimeBundle {graph_namespace: $graph_namespace})
          -[:CONTAINS_MEMORY {graph_namespace: $graph_namespace}]->
          (:RawCapsule {graph_namespace: $graph_namespace})
        RETURN count(*) AS count
        """,
        graph_namespace=graph_namespace,
    )
    return _single_count(result)


def _count_label(tx: object, graph_namespace: str, label: str) -> int:
    _validate_cypher_token(label)
    result = tx.run(
        f"""
        MATCH (n:{label} {{graph_namespace: $graph_namespace}})
        RETURN count(n) AS count
        """,
        graph_namespace=graph_namespace,
    )
    return _single_count(result)


def _count_relationship(tx: object, graph_namespace: str, relationship_type: str) -> int:
    _validate_cypher_token(relationship_type)
    result = tx.run(
        f"""
        MATCH ()-[r:{relationship_type} {{graph_namespace: $graph_namespace}}]->()
        RETURN count(r) AS count
        """,
        graph_namespace=graph_namespace,
    )
    return _single_count(result)


def _count_vessel_relationships(tx: object, graph_namespace: str) -> int:
    result = tx.run(
        """
        MATCH ()-[r {graph_namespace: $graph_namespace}]->()
        WHERE r.display_relationship_type IS NOT NULL
        RETURN count(r) AS count
        """,
        graph_namespace=graph_namespace,
    )
    return _single_count(result)


def _required_property_missing_count(tx: object, graph_namespace: str) -> int:
    result = tx.run(
        """
        MATCH (n:VesselRecord {graph_namespace: $graph_namespace})
        WHERE n.data_id IS NULL
           OR n.generated_by IS NULL
           OR n.info_class IS NULL
           OR n.semantic_judgement_status IS NULL
           OR n.payload_json IS NULL
        RETURN count(n) AS count
        """,
        graph_namespace=graph_namespace,
    )
    return _single_count(result)


def _required_property_missing_samples(tx: object, graph_namespace: str) -> list[str]:
    result = tx.run(
        """
        MATCH (n:VesselRecord {graph_namespace: $graph_namespace})
        WHERE n.data_id IS NULL
           OR n.generated_by IS NULL
           OR n.info_class IS NULL
           OR n.semantic_judgement_status IS NULL
           OR n.payload_json IS NULL
        RETURN collect(coalesce(n.data_id, "<missing-data-id>"))[0..5] AS samples
        """,
        graph_namespace=graph_namespace,
    )
    single = getattr(result, "single", None)
    if callable(single):
        record = single() or {}
        samples = record.get("samples", [])
        if isinstance(samples, list):
            return [item for item in samples if isinstance(item, str)]
    return []


def _readback_failure_reason(checks: _ReadbackChecks) -> str | None:
    if (checks.core_path_count or 0) < 1:
        return "CoreEgo -> TimeAxis -> TimeBundle -> RawCapsule path was not found."
    required_positive_counts = {
        "vessel_record_count": checks.vessel_record_count,
        "vessel_relationship_count": checks.vessel_relationship_count,
        "core_ego_count": checks.core_ego_count,
        "time_axis_count": checks.time_axis_count,
        "time_bundle_count": checks.time_bundle_count,
        "raw_capsule_count": checks.raw_capsule_count,
        "has_axis_count": checks.has_axis_count,
        "has_bundle_count": checks.has_bundle_count,
        "contains_memory_count": checks.contains_memory_count,
    }
    for field_name, count in required_positive_counts.items():
        if (count or 0) < 1:
            return f"{field_name} is zero."
    if (checks.required_property_missing_count or 0) > 0:
        return "Some VesselRecord nodes are missing required provenance properties."
    return None


def _config_failure(config: GraphVesselNeo4jConfig) -> tuple[str, str] | None:
    if not config.uri or not config.user or not config.database:
        return (
            "neo4j_config_missing",
            "Neo4j uri/user/database config is incomplete.",
        )
    if config.password is None and not config.allow_no_auth:
        return (
            "neo4j_config_missing",
            "Neo4j password is not configured. Set SONGRYEON_NEO4J_PASSWORD or pass --password.",
        )
    return None


def _empty_checks() -> _ReadbackChecks:
    return _ReadbackChecks(
        core_path_count=None,
        vessel_record_count=None,
        vessel_relationship_count=None,
        core_ego_count=None,
        time_axis_count=None,
        time_bundle_count=None,
        raw_capsule_count=None,
        has_axis_count=None,
        has_bundle_count=None,
        contains_memory_count=None,
        required_property_missing_count=None,
        required_property_missing_samples=[],
    )


def _validate_readback_result(result: GraphVesselNeo4jReadbackResultFrame) -> None:
    if result.generated_by != GRAPH_VESSEL_NEO4J_READBACK_GENERATOR:
        raise ValueError("GraphVesselNeo4jReadbackResultFrame.generated_by must be readback verifier")
    if result.info_class != "absolute":
        raise ValueError("GraphVesselNeo4jReadbackResultFrame.info_class must be absolute")
    if result.semantic_judgement_status != "not_run":
        raise ValueError("GraphVesselNeo4jReadbackResultFrame.semantic_judgement_status must be not_run")
    if result.readback_status not in GRAPH_VESSEL_NEO4J_READBACK_STATUSES:
        raise ValueError("GraphVesselNeo4jReadbackResultFrame.readback_status is invalid")
    if result.readback_status == "passed" and not result.core_path_exists:
        raise ValueError("passed readback must have core_path_exists=True")


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
            raise ValueError(f"Neo4j readback result data_id collision with different type: {data_id}")
        if existing.payload != payload:
            raise ValueError(f"Neo4j readback result data_id collision with different payload: {data_id}")
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


def _validate_cypher_token(value: str) -> None:
    if not value or not value.replace("_", "").isalnum() or not value[0].isalpha():
        raise ValueError(f"unsafe Neo4j token: {value}")


def _stable_suffix(value: str) -> str:
    return value.replace(":", "_").replace("/", "_").replace("\\", "_")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


__all__ = [
    "GRAPH_VESSEL_NEO4J_READBACK_GENERATOR",
    "GRAPH_VESSEL_NEO4J_READBACK_POLICY_ID",
    "GRAPH_VESSEL_NEO4J_READBACK_RESULT_DATA_TYPE",
    "GRAPH_VESSEL_NEO4J_READBACK_STATUSES",
    "GraphVesselNeo4jReadbackResultFrame",
    "RecordedGraphVesselNeo4jReadbackResult",
    "graph_vessel_neo4j_readback_result_id",
    "readback_graph_vessel_from_neo4j",
    "record_graph_vessel_neo4j_readback_result",
]
