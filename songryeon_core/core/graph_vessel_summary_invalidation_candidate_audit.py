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


GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_DATA_TYPE = (
    "graph_vessel:summary_invalidation_candidate_audit_result"
)
GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_GENERATOR = (
    "CODE:GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDITOR"
)
GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_POLICY_ID = (
    "VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_V0"
)
GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_SCHEMA_NAME = (
    "GraphVesselSummaryInvalidationCandidateAuditFrame"
)
GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_STATUSES = {
    "passed",
    "empty",
    "adapter_unavailable",
    "read_failed",
}

Neo4jDriverFactory = Callable[..., Any]


@dataclass(frozen=True)
class GraphVesselSummaryInvalidationCandidateAuditFrame:
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
    source_lineage_count: int | None
    changed_lineage_count: int | None
    superseded_source_count: int | None
    invalidation_candidate_count: int | None
    already_invalidated_candidate_count: int | None
    manual_review_candidate_count: int | None
    candidate_records: list[dict[str, str]]
    already_invalidated_records: list[dict[str, str]]
    manual_review_records: list[dict[str, str]]
    changed_source_lineage_frame_ids: list[str]
    changed_source_graph_node_ids: list[str]
    source_data_ids: list[str]
    source_trace_ids: list[str]
    generated_by: str = GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_SCHEMA_NAME


@dataclass(frozen=True)
class RecordedGraphVesselSummaryInvalidationCandidateAudit:
    result: GraphVesselSummaryInvalidationCandidateAuditFrame
    trace_event_id: str
    created_data_ids: list[str]
    existing_data_ids: list[str]


def graph_vessel_summary_invalidation_candidate_audit_result_id(
    batch_id: str,
) -> str:
    if not batch_id:
        raise ValueError("batch_id must not be empty")
    return f"graph_vessel:summary_invalidation_candidate_audit:{_stable_suffix(batch_id)}"


def audit_graph_vessel_summary_invalidation_candidates_from_neo4j(
    *,
    config: GraphVesselNeo4jConfig,
    batch_id: str = "manual_vessel_summary_invalidation_candidate_audit",
    limit: int = 50,
    created_at: str | None = None,
    driver_factory: Neo4jDriverFactory | None = None,
) -> GraphVesselSummaryInvalidationCandidateAuditFrame:
    timestamp = created_at or _now_iso()
    safe_limit = max(1, min(limit, 500))
    base = _AuditBase(
        result_id=graph_vessel_summary_invalidation_candidate_audit_result_id(batch_id),
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
            lineage_records=[],
            summary_records=[],
            limit=safe_limit,
        )

    driver_factory = driver_factory or _load_neo4j_driver_factory()
    if driver_factory is None:
        return _make_result(
            base=base,
            audit_status="adapter_unavailable",
            failure_type="neo4j_driver_missing",
            failure_reason="Python neo4j package is not installed.",
            lineage_records=[],
            summary_records=[],
            limit=safe_limit,
        )

    try:
        auth = None if config.allow_no_auth and config.password is None else (
            config.user,
            config.password,
        )
        driver = driver_factory(config.uri, auth=auth)
        try:
            with driver.session(database=config.database) as session:
                lineage_records, summary_records = session.execute_read(
                    _read_lineages_and_summaries,
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
            lineage_records=[],
            summary_records=[],
            limit=safe_limit,
        )

    return _make_result(
        base=base,
        audit_status="passed" if lineage_records or summary_records else "empty",
        failure_type=None if lineage_records or summary_records else "no_records",
        failure_reason=None
        if lineage_records or summary_records
        else "No source lineage or summary records were found.",
        lineage_records=lineage_records,
        summary_records=summary_records,
        limit=safe_limit,
    )


def record_graph_vessel_summary_invalidation_candidate_audit_result(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    config: GraphVesselNeo4jConfig,
    batch_id: str = "manual_vessel_summary_invalidation_candidate_audit",
    limit: int = 50,
    created_at: str | None = None,
    driver_factory: Neo4jDriverFactory | None = None,
) -> RecordedGraphVesselSummaryInvalidationCandidateAudit:
    result = audit_graph_vessel_summary_invalidation_candidates_from_neo4j(
        config=config,
        batch_id=batch_id,
        limit=limit,
        created_at=created_at,
        driver_factory=driver_factory,
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="graph_vessel_summary_invalidation_candidate_auditor",
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
        data_type=GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_DATA_TYPE,
        payload=asdict(result),
        created_at=result.created_at,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedGraphVesselSummaryInvalidationCandidateAudit(
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
    lineage_records: list[object],
    summary_records: list[object],
    limit: int,
) -> GraphVesselSummaryInvalidationCandidateAuditFrame:
    lineage_items = [_lineage_item_from_record(record) for record in lineage_records]
    summary_items = [_summary_item_from_record(record) for record in summary_records]
    changed_lineages = [
        item for item in lineage_items if item["lineage_status"] == "content_changed"
    ]
    superseded_to_lineage: dict[str, dict[str, object]] = {}
    manual_review_records: list[dict[str, str]] = []
    for lineage in changed_lineages:
        superseded_ids = _string_list(lineage.get("superseded_source_graph_node_ids"))
        if not superseded_ids:
            manual_review_records.append(
                {
                    "source_lineage_frame_id": str(lineage["source_lineage_frame_id"]),
                    "review_reason": "content_changed_lineage_without_superseded_source_ids",
                }
            )
        for superseded_source_id in superseded_ids:
            superseded_to_lineage[superseded_source_id] = lineage

    candidate_records: list[dict[str, str]] = []
    already_invalidated_records: list[dict[str, str]] = []
    for summary in summary_items:
        source_graph_node_ids = _string_list(summary.get("source_graph_node_ids"))
        for source_graph_node_id in source_graph_node_ids:
            lineage = superseded_to_lineage.get(source_graph_node_id)
            if lineage is None:
                continue
            record = {
                "summary_graph_node_id": str(summary["summary_graph_node_id"]),
                "source_lineage_frame_id": str(lineage["source_lineage_frame_id"]),
                "superseded_source_graph_node_id": source_graph_node_id,
                "superseding_source_graph_node_id": str(
                    lineage["active_source_graph_node_id"]
                ),
                "invalidated_reason_code": "source_content_changed",
                "current_validity_status": str(summary["validity_status"]),
                "proposed_validity_status": "invalidated_by_source_change",
                "action_status": "candidate_only_not_applied",
            }
            if summary["validity_status"] == "invalidated_by_source_change":
                already_invalidated_records.append(record)
            else:
                candidate_records.append(record)

    result = GraphVesselSummaryInvalidationCandidateAuditFrame(
        result_id=base.result_id,
        created_at=base.created_at,
        policy_id=GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_POLICY_ID,
        target_adapter_name=base.target_adapter_name,
        vessel_database_name=base.vessel_database_name,
        graph_namespace=base.graph_namespace,
        audit_status=audit_status,
        failure_type=failure_type,
        failure_reason=failure_reason,
        total_summary_count=len(summary_items)
        if audit_status in {"passed", "empty"}
        else None,
        source_lineage_count=len(lineage_items)
        if audit_status in {"passed", "empty"}
        else None,
        changed_lineage_count=len(changed_lineages)
        if audit_status in {"passed", "empty"}
        else None,
        superseded_source_count=len(superseded_to_lineage)
        if audit_status in {"passed", "empty"}
        else None,
        invalidation_candidate_count=len(candidate_records)
        if audit_status in {"passed", "empty"}
        else None,
        already_invalidated_candidate_count=len(already_invalidated_records)
        if audit_status in {"passed", "empty"}
        else None,
        manual_review_candidate_count=len(manual_review_records)
        if audit_status in {"passed", "empty"}
        else None,
        candidate_records=candidate_records[:limit],
        already_invalidated_records=already_invalidated_records[:limit],
        manual_review_records=manual_review_records[:limit],
        changed_source_lineage_frame_ids=_unique_strings(
            [
                str(item["source_lineage_frame_id"])
                for item in changed_lineages
                if isinstance(item.get("source_lineage_frame_id"), str)
            ]
        ),
        changed_source_graph_node_ids=_unique_strings(list(superseded_to_lineage)),
        source_data_ids=_unique_strings(
            [
                *[
                    str(item["source_lineage_frame_id"])
                    for item in changed_lineages
                    if isinstance(item.get("source_lineage_frame_id"), str)
                ],
                *[
                    record["summary_graph_node_id"]
                    for record in [*candidate_records[:limit], *already_invalidated_records[:limit]]
                ],
            ]
        ),
        source_trace_ids=[],
    )
    _validate_result(result)
    return result


def _read_lineages_and_summaries(
    tx: object,
    graph_namespace: str,
) -> tuple[list[object], list[object]]:
    lineage_result = tx.run(
        """
        MATCH (lineage:VesselRecord {graph_namespace: $graph_namespace})
        WHERE lineage.source_data_type = 'graph_source:source_version_lineage_frame'
        RETURN
          lineage.data_id AS source_lineage_frame_id,
          lineage.payload_json AS lineage_payload_json
        ORDER BY lineage.data_id
        LIMIT 50000
        """,
        graph_namespace=graph_namespace,
    )
    summary_result = tx.run(
        """
        MATCH (summary:SummaryGraphNode {graph_namespace: $graph_namespace})
        RETURN
          summary.data_id AS summary_graph_node_id,
          summary.payload_json AS summary_payload_json
        ORDER BY summary.data_id
        LIMIT 50000
        """,
        graph_namespace=graph_namespace,
    )
    return list(lineage_result), list(summary_result)


def _lineage_item_from_record(record: object) -> dict[str, object]:
    payload = _payload(record, "lineage_payload_json")
    return {
        "source_lineage_frame_id": _require_record_str(
            record, "source_lineage_frame_id"
        ),
        "lineage_status": _text(payload.get("lineage_status")),
        "active_source_graph_node_id": _text(payload.get("active_source_graph_node_id")),
        "superseded_source_graph_node_ids": _string_list(
            payload.get("superseded_source_graph_node_ids")
        ),
    }


def _summary_item_from_record(record: object) -> dict[str, object]:
    payload = _payload(record, "summary_payload_json")
    return {
        "summary_graph_node_id": _require_record_str(record, "summary_graph_node_id"),
        "validity_status": _text(payload.get("validity_status")) or "active",
        "source_graph_node_ids": _string_list(payload.get("source_graph_node_ids")),
    }


def _payload(record: object, field_name: str) -> dict[str, object]:
    payload_json = _optional_record_str(record, field_name)
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


def _validate_result(
    result: GraphVesselSummaryInvalidationCandidateAuditFrame,
) -> None:
    if result.audit_status not in GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_STATUSES:
        raise ValueError(
            "GraphVesselSummaryInvalidationCandidateAuditFrame.audit_status is invalid"
        )
    if result.generated_by != GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_GENERATOR:
        raise ValueError(
            "GraphVesselSummaryInvalidationCandidateAuditFrame.generated_by is invalid"
        )
    if result.info_class != "absolute":
        raise ValueError(
            "GraphVesselSummaryInvalidationCandidateAuditFrame.info_class must be absolute"
        )
    if result.semantic_judgement_status != "not_run":
        raise ValueError(
            "GraphVesselSummaryInvalidationCandidateAuditFrame.semantic_judgement_status must be not_run"
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
            raise ValueError(
                f"summary invalidation candidate audit data_id collision: {data_id}"
            )
        if existing.payload != payload:
            raise ValueError(
                "summary invalidation candidate audit data_id collision with different payload: "
                f"{data_id}"
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
        raise ValueError(f"Neo4j invalidation candidate field is missing: {field_name}")
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


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


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


def _stable_suffix(value: str) -> str:
    return value.replace(":", "_").replace("/", "_").replace("\\", "_")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


__all__ = [
    "GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_DATA_TYPE",
    "GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_GENERATOR",
    "GraphVesselSummaryInvalidationCandidateAuditFrame",
    "RecordedGraphVesselSummaryInvalidationCandidateAudit",
    "audit_graph_vessel_summary_invalidation_candidates_from_neo4j",
    "graph_vessel_summary_invalidation_candidate_audit_result_id",
    "record_graph_vessel_summary_invalidation_candidate_audit_result",
]

