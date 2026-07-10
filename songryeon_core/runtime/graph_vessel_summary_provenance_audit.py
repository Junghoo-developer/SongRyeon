from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_vessel_neo4j import graph_vessel_neo4j_config_from_env
from songryeon_core.core.graph_vessel_summary_provenance_audit import (
    record_graph_vessel_summary_provenance_audit_result,
)
from songryeon_core.core.trace_store import TraceStore


def run_local_vessel_summary_provenance_audit(
    *,
    batch_id: str = "manual_vessel_summary_provenance_audit",
    turn_id: str = "turn_vessel_summary_provenance_audit_0001",
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    allow_no_auth: bool = False,
    limit: int = 50,
) -> dict[str, object]:
    """Read-only audit for summary run provenance fields in local Neo4j Vessel."""

    now = _now_iso()
    trace_store = TraceStore()
    data_store = DataStore()
    config = graph_vessel_neo4j_config_from_env(
        uri=uri,
        user=user,
        password=password,
        database=database,
        allow_no_auth=allow_no_auth,
    )
    audit = record_graph_vessel_summary_provenance_audit_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        batch_id=batch_id,
        config=config,
        created_at=now,
        limit=limit,
    )
    result = audit.result
    return {
        "status": "VESSEL_SUMMARY_PROVENANCE_AUDIT_OK"
        if result.audit_status in {"passed", "empty"}
        else "VESSEL_SUMMARY_PROVENANCE_AUDIT_NOT_PASSED",
        "audit_status": result.audit_status,
        "failure_type": result.failure_type,
        "failure_reason": result.failure_reason,
        "target_adapter_name": result.target_adapter_name,
        "vessel_database_name": result.vessel_database_name,
        "graph_namespace": result.graph_namespace,
        "neo4j_uri": config.uri,
        "neo4j_user": config.user,
        "neo4j_password_configured": config.password is not None,
        "neo4j_allow_no_auth": config.allow_no_auth,
        "trace_count": len(trace_store.list_events()),
        "data_record_count": len(data_store.list_records()),
        "audit_result_id": result.result_id,
        "total_summary_count": result.total_summary_count,
        "recorded_provenance_count": result.recorded_provenance_count,
        "legacy_not_recorded_count": result.legacy_not_recorded_count,
        "incomplete_provenance_count": result.incomplete_provenance_count,
        "invalid_provenance_status_count": result.invalid_provenance_status_count,
        "provenance_count_by_status": result.provenance_count_by_status,
        "summary_count_by_data_kind": result.summary_count_by_data_kind,
        "legacy_sample_items": result.legacy_sample_items,
        "incomplete_sample_items": result.incomplete_sample_items,
        "audit_result_frame": asdict(result),
    }


def render_vessel_summary_provenance_audit_text(result: dict[str, object]) -> str:
    lines = [
        f"status: {result.get('status')}",
        f"audit_status: {result.get('audit_status')}",
    ]
    failure_type = result.get("failure_type")
    failure_reason = result.get("failure_reason")
    if failure_type or failure_reason:
        lines.append(f"failure_type: {failure_type}")
        lines.append(f"failure_reason: {failure_reason}")
    lines.extend(
        [
            f"graph_namespace: {result.get('graph_namespace')}",
            f"total_summary_count: {result.get('total_summary_count')}",
            f"recorded_provenance_count: {result.get('recorded_provenance_count')}",
            f"legacy_not_recorded_count: {result.get('legacy_not_recorded_count')}",
            f"incomplete_provenance_count: {result.get('incomplete_provenance_count')}",
            f"invalid_provenance_status_count: {result.get('invalid_provenance_status_count')}",
            f"provenance_count_by_status: {result.get('provenance_count_by_status')}",
            f"summary_count_by_data_kind: {result.get('summary_count_by_data_kind')}",
        ]
    )
    legacy_items = result.get("legacy_sample_items")
    if isinstance(legacy_items, list) and legacy_items:
        lines.append("")
        lines.append("Legacy summary samples")
        for item in legacy_items:
            if not isinstance(item, dict):
                continue
            lines.append(
                "  "
                f"{item.get('data_kind')} "
                f"[{item.get('summary_data_id')}] "
                f"missing={item.get('missing_fields')}"
            )
    incomplete_items = result.get("incomplete_sample_items")
    if isinstance(incomplete_items, list) and incomplete_items:
        lines.append("")
        lines.append("Incomplete/invalid summary samples")
        for item in incomplete_items:
            if not isinstance(item, dict):
                continue
            lines.append(
                "  "
                f"{item.get('data_kind')} "
                f"[{item.get('summary_data_id')}] "
                f"status={item.get('run_provenance_status')} "
                f"missing={item.get('missing_fields')}"
            )
    return "\n".join(lines)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


__all__ = [
    "render_vessel_summary_provenance_audit_text",
    "run_local_vessel_summary_provenance_audit",
]

