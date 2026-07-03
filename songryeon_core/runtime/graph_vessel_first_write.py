from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import record_graph_memory_for_capsules
from songryeon_core.core.graph_memory_export import record_graph_memory_export_packet
from songryeon_core.core.graph_vessel_adapter import record_graph_vessel_write_plan
from songryeon_core.core.graph_vessel_neo4j import (
    GraphVesselNeo4jConfig,
    graph_vessel_neo4j_config_from_env,
    record_graph_vessel_neo4j_write_result,
)
from songryeon_core.core.schemas import NodeMovement, TurnStateCapsule
from songryeon_core.core.songryeon_source_manifest import (
    record_songryeon_core_source_manifest_ingest,
)
from songryeon_core.core.trace_store import TraceStore


def run_local_vessel_first_write(
    *,
    root_path: str | Path = ".",
    batch_id: str = "manual_vessel_first_write",
    turn_id: str = "turn_vessel_first_write_0001",
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    allow_no_auth: bool = False,
    include_source_manifest: bool = False,
    store_text_snapshots: bool = False,
) -> dict[str, object]:
    """Manual opt-in local Vessel first-write runner.

    This builds a tiny graph fixture, creates the export packet and write plan,
    and then attempts the Neo4j write only through the ORDER_160 writer.
    """

    now = _now_iso()
    root = Path(root_path).resolve()
    trace_store = TraceStore()
    data_store = DataStore()
    record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        batch_id=f"{batch_id}:core",
        capsules=[_sample_capsule(turn_id=f"{turn_id}:previous")],
    )
    source_manifest_frame_id = None
    source_ingest_frame_id = None
    if include_source_manifest:
        source_result = record_songryeon_core_source_manifest_ingest(
            trace_store=trace_store,
            data_store=data_store,
            root_path=root,
            turn_id=turn_id,
            batch_id=f"{batch_id}:source_manifest",
            observed_at=now,
            ingested_at=now,
            store_text_snapshots=store_text_snapshots,
        )
        source_manifest_frame_id = source_result.manifest_data_id
        source_ingest_frame_id = source_result.ingest_result.frame_id

    export_result = record_graph_memory_export_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        batch_id=f"{batch_id}:export",
        created_at=now,
    )
    plan_result = record_graph_vessel_write_plan(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        export_packet_id=export_result.packet.packet_id,
        created_at=now,
    )
    config: GraphVesselNeo4jConfig = graph_vessel_neo4j_config_from_env(
        uri=uri,
        user=user,
        password=password,
        database=database,
        allow_no_auth=allow_no_auth,
    )
    write_result = record_graph_vessel_neo4j_write_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        plan_id=plan_result.plan.plan_id,
        config=config,
        created_at=now,
    )

    result_payload = asdict(write_result.result)
    return {
        "status": "VESSEL_FIRST_WRITE_OK"
        if write_result.result.write_status == "written"
        else "VESSEL_FIRST_WRITE_NOT_WRITTEN",
        "write_status": write_result.result.write_status,
        "failure_type": write_result.result.failure_type,
        "failure_reason": write_result.result.failure_reason,
        "target_adapter_name": write_result.result.target_adapter_name,
        "vessel_database_name": write_result.result.vessel_database_name,
        "graph_namespace": write_result.result.graph_namespace,
        "neo4j_uri": config.uri,
        "neo4j_user": config.user,
        "neo4j_password_configured": config.password is not None,
        "neo4j_allow_no_auth": config.allow_no_auth,
        "include_source_manifest": include_source_manifest,
        "store_text_snapshots": store_text_snapshots,
        "trace_count": len(trace_store.list_events()),
        "data_record_count": len(data_store.list_records()),
        "export_packet_id": export_result.packet.packet_id,
        "write_plan_id": plan_result.plan.plan_id,
        "write_result_id": write_result.result.result_id,
        "source_manifest_frame_id": source_manifest_frame_id,
        "source_ingest_frame_id": source_ingest_frame_id,
        "operation_count": plan_result.plan.operation_count,
        "attempted_operation_count": write_result.result.attempted_operation_count,
        "written_operation_count": write_result.result.written_operation_count,
        "operation_count_by_kind": write_result.result.operation_count_by_kind,
        "neo4j_record_node_count": write_result.result.neo4j_record_node_count,
        "neo4j_graph_edge_count": write_result.result.neo4j_graph_edge_count,
        "write_result_frame": result_payload,
    }


def _sample_capsule(turn_id: str) -> TurnStateCapsule:
    return TurnStateCapsule(
        turn_id=turn_id,
        node_movements=[
            NodeMovement(
                movement_id=f"move:{turn_id}:001",
                turn_id=turn_id,
                step_index=1,
                node_id="node_0",
                mode="pre_route_report",
                input_trace_ids=[f"trace:{turn_id}:user"],
                output_trace_ids=[f"trace:{turn_id}:node0"],
                status="completed",
            )
        ],
        trace_event_ids=[
            f"trace:{turn_id}:user",
            f"trace:{turn_id}:node0",
            f"trace:{turn_id}:final",
        ],
        user_input_trace_id=f"trace:{turn_id}:user",
        final_response_trace_id=f"trace:{turn_id}:final",
    )


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


__all__ = ["run_local_vessel_first_write"]
