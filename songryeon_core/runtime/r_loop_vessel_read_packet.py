from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_vessel_neo4j import graph_vessel_neo4j_config_from_env
from songryeon_core.core.r_loop_vessel_read_packet import (
    record_r_loop_vessel_read_packet,
)
from songryeon_core.core.trace_store import TraceStore


def run_local_r_loop_vessel_read_packet(
    *,
    batch_id: str = "manual_r_loop_vessel_read_packet",
    turn_id: str = "turn_r_loop_vessel_read_packet_0001",
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    allow_no_auth: bool = False,
    limit: int = 50,
) -> dict[str, object]:
    """Build a read-only Neo4j Vessel candidate packet for future R loop traversal."""

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
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        batch_id=batch_id,
        config=config,
        created_at=now,
        limit=limit,
    )

    packet_payload = asdict(recorded.packet)
    packet_text = "\n".join(recorded.packet.packet_lines)
    return {
        "status": "R_LOOP_VESSEL_READ_PACKET_OK"
        if recorded.packet.read_status == "passed"
        else "R_LOOP_VESSEL_READ_PACKET_NOT_PASSED",
        "read_status": recorded.packet.read_status,
        "failure_type": recorded.packet.failure_type,
        "failure_reason": recorded.packet.failure_reason,
        "target_adapter_name": recorded.packet.target_adapter_name,
        "vessel_database_name": recorded.packet.vessel_database_name,
        "graph_namespace": recorded.packet.graph_namespace,
        "target_consumer": recorded.packet.target_consumer,
        "neo4j_uri": config.uri,
        "neo4j_user": config.user,
        "neo4j_password_configured": config.password is not None,
        "neo4j_allow_no_auth": config.allow_no_auth,
        "trace_count": len(trace_store.list_events()),
        "data_record_count": len(data_store.list_records()),
        "packet_id": recorded.packet.packet_id,
        "entry_candidate_count": recorded.packet.entry_candidate_count,
        "base_entry_candidate_count": recorded.packet.base_entry_candidate_count,
        "exact_child_expanded_entry_count": (
            recorded.packet.exact_child_expanded_entry_count
        ),
        "exact_child_expansion_truncated": (
            recorded.packet.exact_child_expansion_truncated
        ),
        "summary_candidate_count": recorded.packet.summary_candidate_count,
        "base_summary_candidate_count": recorded.packet.base_summary_candidate_count,
        "summary_child_expanded_count": recorded.packet.summary_child_expanded_count,
        "summary_child_expansion_truncated": (
            recorded.packet.summary_child_expansion_truncated
        ),
        "total_summary_scanned_count": recorded.packet.total_summary_scanned_count,
        "active_summary_candidate_count": recorded.packet.active_summary_candidate_count,
        "skipped_summary_count": recorded.packet.skipped_summary_count,
        "summary_count_by_data_kind": recorded.packet.summary_count_by_data_kind,
        "summary_count_by_depth": recorded.packet.summary_count_by_depth,
        "entry_candidate_records": recorded.packet.entry_candidate_records,
        "summary_candidate_records": recorded.packet.summary_candidate_records,
        "packet_lines": recorded.packet.packet_lines,
        "packet_text": packet_text,
        "read_packet_frame": packet_payload,
    }


def render_r_loop_vessel_read_packet_text(result: dict[str, object]) -> str:
    lines = [
        f"status: {result.get('status')}",
        f"read_status: {result.get('read_status')}",
    ]
    failure_type = result.get("failure_type")
    failure_reason = result.get("failure_reason")
    if failure_type or failure_reason:
        lines.append(f"failure_type: {failure_type}")
        lines.append(f"failure_reason: {failure_reason}")
    lines.append(f"graph_namespace: {result.get('graph_namespace')}")
    lines.append(f"target_consumer: {result.get('target_consumer')}")
    lines.append(f"entry_candidate_count: {result.get('entry_candidate_count')}")
    lines.append(f"base_entry_candidate_count: {result.get('base_entry_candidate_count')}")
    lines.append(
        "exact_child_expanded_entry_count: "
        f"{result.get('exact_child_expanded_entry_count')}"
    )
    lines.append(
        "exact_child_expansion_truncated: "
        f"{result.get('exact_child_expansion_truncated')}"
    )
    lines.append(f"summary_candidate_count: {result.get('summary_candidate_count')}")
    lines.append(
        "base_summary_candidate_count: "
        f"{result.get('base_summary_candidate_count')}"
    )
    lines.append(
        "summary_child_expanded_count: "
        f"{result.get('summary_child_expanded_count')}"
    )
    lines.append(
        "summary_child_expansion_truncated: "
        f"{result.get('summary_child_expansion_truncated')}"
    )
    lines.append(f"total_summary_scanned_count: {result.get('total_summary_scanned_count')}")
    lines.append(f"skipped_summary_count: {result.get('skipped_summary_count')}")
    lines.append(f"summary_count_by_data_kind: {result.get('summary_count_by_data_kind')}")
    lines.append(f"summary_count_by_depth: {result.get('summary_count_by_depth')}")
    packet_text = result.get("packet_text")
    if isinstance(packet_text, str) and packet_text:
        lines.append("")
        lines.append(packet_text)
    return "\n".join(lines)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


__all__ = [
    "render_r_loop_vessel_read_packet_text",
    "run_local_r_loop_vessel_read_packet",
]
