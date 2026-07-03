from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_vessel_neo4j import (
    graph_vessel_neo4j_config_from_env,
)
from songryeon_core.core.graph_vessel_readback import (
    record_graph_vessel_neo4j_readback_result,
)
from songryeon_core.core.trace_store import TraceStore


def run_local_vessel_readback(
    *,
    batch_id: str = "manual_vessel_readback",
    turn_id: str = "turn_vessel_readback_0001",
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    allow_no_auth: bool = False,
) -> dict[str, object]:
    """Read-only Neo4j Vessel check for the current graph vocabulary."""

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
    readback = record_graph_vessel_neo4j_readback_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        batch_id=batch_id,
        config=config,
        created_at=now,
    )

    result_payload = asdict(readback.result)
    return {
        "status": "VESSEL_READBACK_OK"
        if readback.result.readback_status == "passed"
        else "VESSEL_READBACK_NOT_PASSED",
        "readback_status": readback.result.readback_status,
        "failure_type": readback.result.failure_type,
        "failure_reason": readback.result.failure_reason,
        "target_adapter_name": readback.result.target_adapter_name,
        "vessel_database_name": readback.result.vessel_database_name,
        "graph_namespace": readback.result.graph_namespace,
        "neo4j_uri": config.uri,
        "neo4j_user": config.user,
        "neo4j_password_configured": config.password is not None,
        "neo4j_allow_no_auth": config.allow_no_auth,
        "trace_count": len(trace_store.list_events()),
        "data_record_count": len(data_store.list_records()),
        "readback_result_id": readback.result.result_id,
        "core_path_exists": readback.result.core_path_exists,
        "core_path_count": readback.result.core_path_count,
        "vessel_record_count": readback.result.vessel_record_count,
        "vessel_relationship_count": readback.result.vessel_relationship_count,
        "core_ego_count": readback.result.core_ego_count,
        "time_axis_count": readback.result.time_axis_count,
        "time_bundle_count": readback.result.time_bundle_count,
        "raw_capsule_count": readback.result.raw_capsule_count,
        "has_axis_count": readback.result.has_axis_count,
        "has_bundle_count": readback.result.has_bundle_count,
        "contains_memory_count": readback.result.contains_memory_count,
        "required_property_missing_count": readback.result.required_property_missing_count,
        "required_property_missing_samples": readback.result.required_property_missing_samples,
        "readback_result_frame": result_payload,
    }


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


__all__ = ["run_local_vessel_readback"]
