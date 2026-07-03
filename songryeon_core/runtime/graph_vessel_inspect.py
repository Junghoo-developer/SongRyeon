from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_vessel_inspect import (
    record_graph_vessel_neo4j_inspect_result,
)
from songryeon_core.core.graph_vessel_neo4j import (
    graph_vessel_neo4j_config_from_env,
)
from songryeon_core.core.trace_store import TraceStore


def run_local_vessel_inspect(
    *,
    batch_id: str = "manual_vessel_inspect",
    turn_id: str = "turn_vessel_inspect_0001",
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    allow_no_auth: bool = False,
    limit: int = 50,
) -> dict[str, object]:
    """Read-only manual walk over the local Neo4j Vessel tree."""

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
    inspect = record_graph_vessel_neo4j_inspect_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        batch_id=batch_id,
        config=config,
        created_at=now,
        limit=limit,
    )

    result_payload = asdict(inspect.result)
    tree_text = "\n".join(inspect.result.tree_lines)
    return {
        "status": "VESSEL_INSPECT_OK"
        if inspect.result.inspect_status == "passed"
        else "VESSEL_INSPECT_NOT_PASSED",
        "inspect_status": inspect.result.inspect_status,
        "failure_type": inspect.result.failure_type,
        "failure_reason": inspect.result.failure_reason,
        "target_adapter_name": inspect.result.target_adapter_name,
        "vessel_database_name": inspect.result.vessel_database_name,
        "graph_namespace": inspect.result.graph_namespace,
        "neo4j_uri": config.uri,
        "neo4j_user": config.user,
        "neo4j_password_configured": config.password is not None,
        "neo4j_allow_no_auth": config.allow_no_auth,
        "trace_count": len(trace_store.list_events()),
        "data_record_count": len(data_store.list_records()),
        "inspect_result_id": inspect.result.result_id,
        "inspected_path_count": inspect.result.inspected_path_count,
        "core_count": inspect.result.core_count,
        "time_axis_count": inspect.result.time_axis_count,
        "time_bundle_count": inspect.result.time_bundle_count,
        "raw_capsule_count": inspect.result.raw_capsule_count,
        "summary_count": inspect.result.summary_count,
        "active_summary_count": inspect.result.active_summary_count,
        "invalidated_summary_count": inspect.result.invalidated_summary_count,
        "summary_count_by_data_kind": inspect.result.summary_count_by_data_kind,
        "summary_count_by_depth": inspect.result.summary_count_by_depth,
        "summary_sample_items": inspect.result.summary_sample_items,
        "summary_lines": inspect.result.summary_lines,
        "tree_lines": inspect.result.tree_lines,
        "tree_text": tree_text,
        "path_items": inspect.result.path_items,
        "inspect_result_frame": result_payload,
    }


def render_vessel_inspect_text(result: dict[str, object]) -> str:
    lines = [
        f"status: {result.get('status')}",
        f"inspect_status: {result.get('inspect_status')}",
    ]
    failure_type = result.get("failure_type")
    failure_reason = result.get("failure_reason")
    if failure_type or failure_reason:
        lines.append(f"failure_type: {failure_type}")
        lines.append(f"failure_reason: {failure_reason}")
    lines.append(f"graph_namespace: {result.get('graph_namespace')}")
    lines.append(f"inspected_path_count: {result.get('inspected_path_count')}")
    summary_count = result.get("summary_count")
    if summary_count is not None:
        lines.append(f"summary_count: {summary_count}")
        lines.append(f"active_summary_count: {result.get('active_summary_count')}")
        lines.append(
            f"invalidated_summary_count: {result.get('invalidated_summary_count')}"
        )
        lines.append(f"summary_count_by_data_kind: {result.get('summary_count_by_data_kind')}")
        lines.append(f"summary_count_by_depth: {result.get('summary_count_by_depth')}")
    tree_text = result.get("tree_text")
    if isinstance(tree_text, str) and tree_text:
        lines.append("")
        lines.append(tree_text)
    summary_lines = result.get("summary_lines")
    if isinstance(summary_lines, list) and summary_lines:
        lines.append("")
        lines.extend(str(line) for line in summary_lines)
    return "\n".join(lines)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


__all__ = ["render_vessel_inspect_text", "run_local_vessel_inspect"]
