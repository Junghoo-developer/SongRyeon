from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory_store import (
    SONGRYEON_GRAPH_NAMESPACE,
    SONGRYEON_VESSEL_SERVICE_NAME,
)
from songryeon_core.core.graph_vessel_neo4j import GraphVesselNeo4jConfig
from songryeon_core.core.trace_store import TraceStore


GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDIT_DATA_TYPE = (
    "graph_vessel:summary_provenance_audit_result"
)
GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDIT_GENERATOR = (
    "CODE:GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDITOR"
)
GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDIT_POLICY_ID = (
    "VESSEL_SUMMARY_PROVENANCE_AUDIT_V0"
)
GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDIT_SCHEMA_NAME = (
    "GraphVesselSummaryProvenanceAuditFrame"
)
GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDIT_STATUSES = {
    "passed",
    "empty",
    "adapter_unavailable",
    "read_failed",
}
SUMMARY_PROVENANCE_REQUIRED_FIELDS = (
    "summary_run_id",
    "night_turn_id",
    "night_batch_id",
    "summary_created_at",
    "run_provenance_status",
)

Neo4jDriverFactory = Callable[..., Any]


@dataclass(frozen=True)
class GraphVesselSummaryProvenanceAuditFrame:
    result_id: str
    created_at: str
    policy_id: str
    target_adapter_name: str
    vessel_database_name: str
    graph_namespace: str
    audit_status: str
    failure_type: str | None
    failure_reason: str | None
    total_summary_count: int | None
    recorded_provenance_count: int | None
    legacy_not_recorded_count: int | None
    incomplete_provenance_count: int | None
    invalid_provenance_status_count: int | None
    provenance_count_by_status: dict[str, int]
    summary_count_by_data_kind: dict[str, int]
    legacy_sample_items: list[dict[str, object]]
    incomplete_sample_items: list[dict[str, object]]
    source_data_ids: list[str]
    source_trace_ids: list[str]
    generated_by: str = GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDIT_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDIT_SCHEMA_NAME


@dataclass(frozen=True)
class RecordedGraphVesselSummaryProvenanceAudit:
    result: GraphVesselSummaryProvenanceAuditFrame
    trace_event_id: str
    created_data_ids: list[str]
    existing_data_ids: list[str]


def graph_vessel_summary_provenance_audit_result_id(batch_id: str) -> str:
    if not batch_id:
        raise ValueError("batch_id must not be empty")
    return f"graph_vessel:summary_provenance_audit:{_stable_suffix(batch_id)}"


def audit_graph_vessel_summary_provenance_from_neo4j(
    *,
    config: GraphVesselNeo4jConfig,
    batch_id: str = "manual_vessel_summary_provenance_audit",
    limit: int = 50,
    created_at: str | None = None,
    driver_factory: Neo4jDriverFactory | None = None,
) -> GraphVesselSummaryProvenanceAuditFrame:
    timestamp = created_at or _now_iso()
    safe_limit = max(1, min(limit, 500))
    base = _AuditBase(
        result_id=graph_vessel_summary_provenance_audit_result_id(batch_id),
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
            audit_status="adapter_unavailable",
            failure_type=failure_type,
            failure_reason=failure_reason,
            summary_records=[],
            limit=safe_limit,
            total_summary_count=None,
        )

    driver_factory = driver_factory or _load_neo4j_driver_factory()
    if driver_factory is None:
        return _make_result(
            base=base,
            audit_status="adapter_unavailable",
            failure_type="neo4j_driver_missing",
            failure_reason="Python neo4j package is not installed.",
            summary_records=[],
            limit=safe_limit,
            total_summary_count=None,
        )

    try:
        auth = None if config.allow_no_auth and config.password is None else (
            config.user,
            config.password,
        )
        driver = driver_factory(config.uri, auth=auth)
        try:
            with driver.session(database=config.database) as session:
                summary_records = session.execute_read(
                    _read_summary_records,
                    SONGRYEON_GRAPH_NAMESPACE,
                )
        finally:
            close = getattr(driver, "close", None)
            if callable(close):
                close()
    except Exception as exc:
        return _make_result(
            base=base,
            audit_status="read_failed",
            failure_type="neo4j_read_failed",
            failure_reason=f"{type(exc).__name__}: {exc}",
            summary_records=[],
            limit=safe_limit,
            total_summary_count=None,
        )

    return _make_result(
        base=base,
        audit_status="passed" if summary_records else "empty",
        failure_type=None if summary_records else "no_summary_nodes",
        failure_reason=None if summary_records else "No SummaryGraphNode records were found.",
        summary_records=summary_records,
        limit=safe_limit,
        total_summary_count=len(summary_records),
    )


def record_graph_vessel_summary_provenance_audit_result(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    config: GraphVesselNeo4jConfig,
    batch_id: str = "manual_vessel_summary_provenance_audit",
    limit: int = 50,
    created_at: str | None = None,
    driver_factory: Neo4jDriverFactory | None = None,
) -> RecordedGraphVesselSummaryProvenanceAudit:
    result = audit_graph_vessel_summary_provenance_from_neo4j(
        config=config,
        batch_id=batch_id,
        limit=limit,
        created_at=created_at,
        driver_factory=driver_factory,
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="graph_vessel_summary_provenance_auditor",
        event_type="node_output",
        timestamp=result.created_at,
        input_ref=[],
        output_ref=[result.result_id],
        schema_status="passed"
        if result.audit_status in {"passed", "empty"}
        else "failed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=result.result_id,
        data_type=GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDIT_DATA_TYPE,
        payload=asdict(result),
        created_at=result.created_at,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedGraphVesselSummaryProvenanceAudit(
        result=result,
        trace_event_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


@dataclass(frozen=True)
class _AuditBase:
    result_id: str
    created_at: str
    target_adapter_name: str
    vessel_database_name: str
    graph_namespace: str


def _make_result(
    *,
    base: _AuditBase,
    audit_status: str,
    failure_type: str | None,
    failure_reason: str | None,
    summary_records: list[object],
    limit: int,
    total_summary_count: int | None,
) -> GraphVesselSummaryProvenanceAuditFrame:
    audit_items = [_audit_item_from_record(record) for record in summary_records]
    legacy_items = [
        item for item in audit_items if item["provenance_classification"] == "legacy"
    ]
    incomplete_items = [
        item
        for item in audit_items
        if item["provenance_classification"] in {"incomplete", "invalid_status"}
    ]
    result = GraphVesselSummaryProvenanceAuditFrame(
        result_id=base.result_id,
        created_at=base.created_at,
        policy_id=GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDIT_POLICY_ID,
        target_adapter_name=base.target_adapter_name,
        vessel_database_name=base.vessel_database_name,
        graph_namespace=base.graph_namespace,
        audit_status=audit_status,
        failure_type=failure_type,
        failure_reason=failure_reason,
        total_summary_count=total_summary_count,
        recorded_provenance_count=sum(
            1
            for item in audit_items
            if item["provenance_classification"] == "recorded"
        )
        if total_summary_count is not None
        else None,
        legacy_not_recorded_count=len(legacy_items)
        if total_summary_count is not None
        else None,
        incomplete_provenance_count=sum(
            1
            for item in audit_items
            if item["provenance_classification"] == "incomplete"
        )
        if total_summary_count is not None
        else None,
        invalid_provenance_status_count=sum(
            1
            for item in audit_items
            if item["provenance_classification"] == "invalid_status"
        )
        if total_summary_count is not None
        else None,
        provenance_count_by_status=_count_by_status(audit_items),
        summary_count_by_data_kind=_count_by_data_kind(audit_items),
        legacy_sample_items=legacy_items[:limit],
        incomplete_sample_items=incomplete_items[:limit],
        source_data_ids=_unique_strings(
            [
                item["summary_data_id"]
                for item in [*legacy_items[:limit], *incomplete_items[:limit]]
                if isinstance(item.get("summary_data_id"), str)
            ]
        ),
        source_trace_ids=[],
    )
    _validate_result(result)
    return result


def _read_summary_records(tx: object, graph_namespace: str) -> list[object]:
    result = tx.run(
        """
        MATCH (summary:SummaryGraphNode {graph_namespace: $graph_namespace})
        RETURN
          summary.data_id AS summary_data_id,
          coalesce(summary.display_name, summary.data_id) AS summary_display_name,
          summary.data_kind AS summary_data_kind,
          summary.info_class AS summary_info_class,
          summary.generated_by AS summary_generated_by,
          summary.payload_json AS summary_payload_json
        ORDER BY summary.data_kind, summary.data_id
        LIMIT 50000
        """,
        graph_namespace=graph_namespace,
    )
    return list(result)


def _audit_item_from_record(record: object) -> dict[str, object]:
    payload = _summary_payload(record)
    summary_data_id = _require_record_str(record, "summary_data_id")
    status = _text(payload.get("run_provenance_status"))
    missing_fields = [
        field_name
        for field_name in SUMMARY_PROVENANCE_REQUIRED_FIELDS
        if not _text(payload.get(field_name))
    ]
    has_any_provenance_field = any(
        _text(payload.get(field_name))
        for field_name in SUMMARY_PROVENANCE_REQUIRED_FIELDS
    )
    if not has_any_provenance_field:
        classification = "legacy"
        effective_status = "legacy_not_recorded"
    elif status not in {"recorded", "legacy_not_recorded", "backfilled_from_trace"}:
        classification = "invalid_status"
        effective_status = status or "missing_status"
    elif missing_fields:
        classification = "incomplete"
        effective_status = status
    else:
        classification = "recorded"
        effective_status = status
    return {
        "summary_data_id": summary_data_id,
        "summary_display_name": _require_record_str(record, "summary_display_name"),
        "data_kind": _optional_record_str(record, "summary_data_kind")
        or _text(payload.get("data_kind"))
        or "unknown",
        "summary_depth": _optional_int(payload.get("summary_depth")),
        "validity_status": _text(payload.get("validity_status")) or "unknown",
        "run_provenance_status": effective_status,
        "provenance_classification": classification,
        "missing_fields": missing_fields,
        "summary_run_id": _text(payload.get("summary_run_id")),
        "night_turn_id": _text(payload.get("night_turn_id")),
        "night_batch_id": _text(payload.get("night_batch_id")),
        "summary_created_at": _text(payload.get("summary_created_at")),
    }


def _count_by_status(items: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(item.get("run_provenance_status") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _count_by_data_kind(items: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(item.get("data_kind") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _summary_payload(record: object) -> dict[str, object]:
    payload_json = _optional_record_str(record, "summary_payload_json")
    if not payload_json:
        return {}
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


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


def _validate_result(result: GraphVesselSummaryProvenanceAuditFrame) -> None:
    if result.audit_status not in GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDIT_STATUSES:
        raise ValueError("GraphVesselSummaryProvenanceAuditFrame.audit_status is invalid")
    if result.generated_by != GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDIT_GENERATOR:
        raise ValueError("GraphVesselSummaryProvenanceAuditFrame.generated_by is invalid")
    if result.info_class != "absolute":
        raise ValueError("GraphVesselSummaryProvenanceAuditFrame.info_class must be absolute")
    if result.semantic_judgement_status != "not_run":
        raise ValueError(
            "GraphVesselSummaryProvenanceAuditFrame.semantic_judgement_status must be not_run"
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
            raise ValueError(f"summary provenance audit data_id collision: {data_id}")
        if existing.payload != payload:
            raise ValueError(
                f"summary provenance audit data_id collision with different payload: {data_id}"
            )
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


def _require_record_str(record: object, field_name: str) -> str:
    value = _record_value(record, field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Neo4j summary provenance audit field is missing: {field_name}")
    return value


def _optional_record_str(record: object, field_name: str) -> str | None:
    value = _record_value(record, field_name)
    return value if isinstance(value, str) and value else None


def _record_value(record: object, field_name: str) -> object:
    try:
        return record[field_name]  # type: ignore[index]
    except (KeyError, TypeError):
        data = getattr(record, "data", None)
        if callable(data):
            payload = data()
            if isinstance(payload, dict):
                return payload.get(field_name)
    return None


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _stable_suffix(value: str) -> str:
    return value.replace(":", "_").replace("/", "_").replace("\\", "_")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


__all__ = [
    "GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDIT_DATA_TYPE",
    "GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDIT_GENERATOR",
    "GraphVesselSummaryProvenanceAuditFrame",
    "RecordedGraphVesselSummaryProvenanceAudit",
    "audit_graph_vessel_summary_provenance_from_neo4j",
    "graph_vessel_summary_provenance_audit_result_id",
    "record_graph_vessel_summary_provenance_audit_result",
]

