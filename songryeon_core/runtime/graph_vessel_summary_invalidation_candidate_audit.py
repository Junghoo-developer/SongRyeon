from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_vessel_neo4j import graph_vessel_neo4j_config_from_env
from songryeon_core.core.graph_vessel_summary_invalidation_candidate_audit import (
    record_graph_vessel_summary_invalidation_candidate_audit_result,
)
from songryeon_core.core.trace_store import TraceStore


def run_local_vessel_summary_invalidation_candidate_audit(
    *,
    batch_id: str = "manual_vessel_summary_invalidation_candidate_audit",
    turn_id: str = "turn_vessel_summary_invalidation_candidate_audit_0001",
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    allow_no_auth: bool = False,
    limit: int = 50,
) -> dict[str, object]:
    """Read-only audit for summaries affected by changed source versions."""

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
    audit = record_graph_vessel_summary_invalidation_candidate_audit_result(
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
        "status": "VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_OK"
        if result.audit_status in {"passed", "empty"}
        else "VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_NOT_PASSED",
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
        "source_lineage_count": result.source_lineage_count,
        "changed_lineage_count": result.changed_lineage_count,
        "superseded_source_count": result.superseded_source_count,
        "invalidation_candidate_count": result.invalidation_candidate_count,
        "already_invalidated_candidate_count": (
            result.already_invalidated_candidate_count
        ),
        "manual_review_candidate_count": result.manual_review_candidate_count,
        "candidate_records": result.candidate_records,
        "already_invalidated_records": result.already_invalidated_records,
        "manual_review_records": result.manual_review_records,
        "changed_source_lineage_frame_ids": result.changed_source_lineage_frame_ids,
        "changed_source_graph_node_ids": result.changed_source_graph_node_ids,
        "audit_result_frame": asdict(result),
    }


def render_vessel_summary_invalidation_candidate_audit_text(
    result: dict[str, object],
) -> str:
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
            f"source_lineage_count: {result.get('source_lineage_count')}",
            f"changed_lineage_count: {result.get('changed_lineage_count')}",
            f"superseded_source_count: {result.get('superseded_source_count')}",
            f"invalidation_candidate_count: {result.get('invalidation_candidate_count')}",
            "already_invalidated_candidate_count: "
            f"{result.get('already_invalidated_candidate_count')}",
            f"manual_review_candidate_count: {result.get('manual_review_candidate_count')}",
        ]
    )
    candidate_records = result.get("candidate_records")
    if isinstance(candidate_records, list) and candidate_records:
        lines.append("")
        lines.append("Invalidation candidate samples")
        for record in candidate_records:
            if not isinstance(record, dict):
                continue
            lines.append(
                "  "
                f"{record.get('summary_graph_node_id')} "
                f"because {record.get('superseded_source_graph_node_id')} "
                f"-> {record.get('superseding_source_graph_node_id')}"
            )
    manual_records = result.get("manual_review_records")
    if isinstance(manual_records, list) and manual_records:
        lines.append("")
        lines.append("Manual review samples")
        for record in manual_records:
            if not isinstance(record, dict):
                continue
            lines.append(
                "  "
                f"{record.get('source_lineage_frame_id')} "
                f"reason={record.get('review_reason')}"
            )
    return "\n".join(lines)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


__all__ = [
    "render_vessel_summary_invalidation_candidate_audit_text",
    "run_local_vessel_summary_invalidation_candidate_audit",
]

