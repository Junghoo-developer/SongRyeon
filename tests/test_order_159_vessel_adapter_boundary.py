from __future__ import annotations

from dataclasses import asdict

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import record_graph_memory_for_capsules
from songryeon_core.core.graph_memory_export import (
    GRAPH_MEMORY_EXPORT_PACKET_DATA_TYPE,
    record_graph_memory_export_packet,
)
from songryeon_core.core.graph_memory_store import (
    SONGRYEON_GRAPH_NAMESPACE,
    SONGRYEON_VESSEL_DATABASE_NAME,
    SONGRYEON_VESSEL_SERVICE_NAME,
)
from songryeon_core.core.graph_vessel_adapter import (
    GRAPH_VESSEL_ADAPTER_BOUNDARY_GENERATOR,
    GRAPH_VESSEL_WRITE_PLAN_DATA_TYPE,
    graph_vessel_write_plan_id,
    record_graph_vessel_write_plan,
)
from songryeon_core.core.schemas import NodeMovement, TurnStateCapsule
from songryeon_core.core.songryeon_source_manifest import (
    record_songryeon_core_source_manifest_ingest,
)
from songryeon_core.core.trace_store import TraceStore


OBSERVED_AT = "2026-07-01T19:00:00"
INGESTED_AT = "2026-07-01T19:00:01"
EXPORTED_AT = "2026-07-01T19:00:02"
PLANNED_AT = "2026-07-01T19:00:03"


def test_vessel_write_plan_builds_ordered_no_write_operations(tmp_path) -> None:
    root = _sample_repo(tmp_path)
    trace_store, data_store, export_packet_id = _store_with_export_packet(root)

    result = record_graph_vessel_write_plan(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_159",
        export_packet_id=export_packet_id,
        created_at=PLANNED_AT,
    )

    plan = result.plan
    assert plan.plan_id == graph_vessel_write_plan_id("batch_order_159_export")
    assert plan.export_packet_id == export_packet_id
    assert plan.generated_by == GRAPH_VESSEL_ADAPTER_BOUNDARY_GENERATOR
    assert plan.info_class == "absolute"
    assert plan.semantic_judgement_status == "not_run"
    assert plan.external_write_status == "not_run"
    assert plan.plan_status == "ready_to_write"
    assert plan.block_reason is None
    assert plan.target_adapter_name == SONGRYEON_VESSEL_SERVICE_NAME
    assert plan.vessel_database_name == SONGRYEON_VESSEL_DATABASE_NAME
    assert plan.graph_namespace == SONGRYEON_GRAPH_NAMESPACE
    assert plan.operation_count == len(plan.operations)
    assert plan.operation_count_by_kind["upsert_graph_node"] > 0
    assert plan.operation_count_by_kind["upsert_graph_edge"] > 0
    assert plan.operation_count_by_kind["upsert_source_payload"] > 0
    assert plan.operation_count_by_kind["upsert_support_record"] > 0
    assert {operation.external_write_status for operation in plan.operations} == {"not_run"}

    operation_kinds = [operation.operation_kind for operation in plan.operations]
    assert operation_kinds == sorted(
        operation_kinds,
        key={
            "upsert_source_payload": 0,
            "upsert_graph_node": 1,
            "upsert_graph_edge": 2,
            "upsert_support_record": 3,
        }.__getitem__,
    )

    record = data_store.require_record(plan.plan_id)
    assert record.data_type == GRAPH_VESSEL_WRITE_PLAN_DATA_TYPE
    assert record.payload["operation_count"] == plan.operation_count
    assert result.created_data_ids == [plan.plan_id]


def test_vessel_write_plan_blocks_failed_integrity_export_packet() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    data_store.create_record(
        data_id="graph:edge:contains:graph:missing_parent:graph:missing_child",
        data_type="graph_memory:edge:CONTAINS",
        payload={
            "edge_id": "graph:edge:contains:graph:missing_parent:graph:missing_child",
            "edge_kind": "CONTAINS",
            "from_node_id": "graph:missing_parent",
            "to_node_id": "graph:missing_child",
            "source_data_ids": ["graph:missing_parent", "graph:missing_child"],
        },
    )
    export_result = record_graph_memory_export_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_159",
        batch_id="batch_order_159_failed_integrity",
        created_at=EXPORTED_AT,
    )

    result = record_graph_vessel_write_plan(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_159",
        export_packet_id=export_result.packet.packet_id,
        created_at=PLANNED_AT,
    )

    plan = result.plan
    assert plan.plan_status == "blocked_integrity_failed"
    assert plan.block_reason == "CODE_STATUS:graph_integrity_failed"
    assert plan.operations == []
    assert plan.operation_count == 0
    assert plan.external_write_status == "not_run"
    assert plan.graph_integrity_status == "failed"


def test_vessel_write_plan_rejects_wrong_target_adapter(tmp_path) -> None:
    root = _sample_repo(tmp_path)
    trace_store, data_store, export_packet_id = _store_with_export_packet(root)
    packet_record = data_store.require_record(export_packet_id)
    payload = dict(packet_record.payload)
    payload["target_adapter_name"] = "wrong-adapter"
    data_store.create_record(
        data_id="graph_memory:export_packet:wrong_target",
        data_type=GRAPH_MEMORY_EXPORT_PACKET_DATA_TYPE,
        payload=payload,
    )

    with pytest.raises(ValueError, match="unexpected target adapter name"):
        record_graph_vessel_write_plan(
            trace_store=trace_store,
            data_store=data_store,
            turn_id="turn_order_159",
            export_packet_id="graph_memory:export_packet:wrong_target",
            created_at=PLANNED_AT,
        )


def test_vessel_write_plan_is_idempotent_for_same_packet_and_timestamp(tmp_path) -> None:
    root = _sample_repo(tmp_path)
    trace_store, data_store, export_packet_id = _store_with_export_packet(root)

    first = record_graph_vessel_write_plan(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_159",
        export_packet_id=export_packet_id,
        created_at=PLANNED_AT,
    )
    second = record_graph_vessel_write_plan(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_159",
        export_packet_id=export_packet_id,
        created_at=PLANNED_AT,
    )

    assert first.created_data_ids == [first.plan.plan_id]
    assert second.created_data_ids == []
    assert second.existing_data_ids == [first.plan.plan_id]
    assert asdict(first.plan) == asdict(second.plan)


def test_vessel_write_plan_does_not_create_semantic_fields(tmp_path) -> None:
    root = _sample_repo(tmp_path)
    trace_store, data_store, export_packet_id = _store_with_export_packet(root)

    result = record_graph_vessel_write_plan(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_159",
        export_packet_id=export_packet_id,
        created_at=PLANNED_AT,
    )

    payload = data_store.require_record(result.plan.plan_id).payload
    for forbidden_field in (
        "summary",
        "semantic_topic",
        "topic_label",
        "importance_score",
        "relevance_reason",
        "meaning_cluster",
        "embedding_id",
    ):
        assert forbidden_field not in payload
    assert payload["generated_by"] == GRAPH_VESSEL_ADAPTER_BOUNDARY_GENERATOR
    assert payload["info_class"] == "absolute"
    assert payload["semantic_judgement_status"] == "not_run"


def _store_with_export_packet(root) -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_159_core",
        batch_id="batch_order_159_core",
        capsules=[_sample_capsule("turn_order_159_previous")],
    )
    record_songryeon_core_source_manifest_ingest(
        trace_store=trace_store,
        data_store=data_store,
        root_path=root,
        turn_id="turn_order_159_source",
        batch_id="batch_order_159_source",
        observed_at=OBSERVED_AT,
        ingested_at=INGESTED_AT,
    )
    export_result = record_graph_memory_export_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_159_export",
        batch_id="batch_order_159_export",
        created_at=EXPORTED_AT,
    )
    return trace_store, data_store, export_result.packet.packet_id


def _sample_repo(tmp_path):
    root = tmp_path / "repo"
    (root / "Administrative_Reform_1" / "04_Orders").mkdir(parents=True)
    (root / "Administrative_Reform_1" / "05_Execution_Records").mkdir(parents=True)
    (root / "songryeon_core").mkdir()
    (root / "tests").mkdir()

    (root / "AGENTS.md").write_text("# agent rules\n", encoding="utf-8")
    (root / "README.md").write_text("# readme\n", encoding="utf-8")
    (root / "Administrative_Reform_1" / "04_Orders" / "ORDER_001.md").write_text(
        "# order\n",
        encoding="utf-8",
    )
    (root / "Administrative_Reform_1" / "05_Execution_Records" / "note.md").write_text(
        "# note\n",
        encoding="utf-8",
    )
    (root / "main.py").write_text("print('main')\n", encoding="utf-8")
    (root / "songryeon_core" / "module.py").write_text(
        "def run():\n    return 1\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_module.py").write_text(
        "def test_run():\n    assert True\n",
        encoding="utf-8",
    )
    return root


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
