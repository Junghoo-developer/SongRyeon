from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import record_graph_memory_for_capsules
from songryeon_core.core.graph_memory_export import (
    GRAPH_MEMORY_EXPORT_PACKET_DATA_TYPE,
    GRAPH_MEMORY_EXPORT_PACKET_GENERATOR,
    GRAPH_MEMORY_EXPORT_TARGET_ADAPTER,
    graph_memory_export_packet_id,
    record_graph_memory_export_packet,
)
from songryeon_core.core.graph_source_ingest import (
    GRAPH_SOURCE_TEXT_SNAPSHOT_DATA_TYPE,
)
from songryeon_core.core.schemas import NodeMovement, TurnStateCapsule
from songryeon_core.core.songryeon_source_manifest import (
    SONGRYEON_CORE_SOURCE_MANIFEST_DATA_TYPE,
    record_songryeon_core_source_manifest_ingest,
)
from songryeon_core.core.trace_store import TraceStore


OBSERVED_AT = "2026-07-01T18:00:00"
INGESTED_AT = "2026-07-01T18:00:01"
EXPORTED_AT = "2026-07-01T18:00:02"


def test_export_packet_collects_graph_and_source_records(tmp_path) -> None:
    root = _sample_repo(tmp_path)
    trace_store, data_store = _graph_and_source_store(root)

    result = record_graph_memory_export_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_158",
        batch_id="batch_order_158_export",
        created_at=EXPORTED_AT,
    )

    packet = result.packet
    assert packet.packet_id == graph_memory_export_packet_id("batch_order_158_export")
    assert packet.generated_by == GRAPH_MEMORY_EXPORT_PACKET_GENERATOR
    assert packet.info_class == "absolute"
    assert packet.semantic_judgement_status == "not_run"
    assert packet.external_write_status == "not_run"
    assert packet.target_adapter_name == GRAPH_MEMORY_EXPORT_TARGET_ADAPTER
    assert packet.graph_integrity_status == "passed"
    assert packet.graph_integrity_summary["passed"] is True

    assert packet.graph_node_data_ids
    assert packet.graph_edge_data_ids
    assert packet.graph_snapshot_data_ids
    assert packet.core_ego_time_axis_frame_ids
    assert packet.rloop_guide_packet_data_ids
    assert packet.source_file_metadata_data_ids
    assert packet.source_text_snapshot_data_ids
    assert packet.source_ingest_frame_data_ids
    assert packet.source_manifest_frame_data_ids
    assert set(packet.source_text_snapshot_data_ids).issubset(packet.included_data_ids)

    record = data_store.require_record(packet.packet_id)
    assert record.data_type == GRAPH_MEMORY_EXPORT_PACKET_DATA_TYPE
    assert record.payload["included_data_ids"] == packet.included_data_ids
    assert result.created_data_ids == [packet.packet_id]
    assert data_store.require_record(packet.source_text_snapshot_data_ids[0]).data_type == (
        GRAPH_SOURCE_TEXT_SNAPSHOT_DATA_TYPE
    )
    assert data_store.require_record(packet.source_manifest_frame_data_ids[0]).data_type == (
        SONGRYEON_CORE_SOURCE_MANIFEST_DATA_TYPE
    )


def test_export_packet_excludes_unrelated_datastore_records(tmp_path) -> None:
    root = _sample_repo(tmp_path)
    trace_store, data_store = _graph_and_source_store(root)
    data_store.create_record(
        data_id="node_output:unrelated",
        data_type="node_output:test",
        payload={"text": "not graph memory"},
    )

    result = record_graph_memory_export_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_158",
        batch_id="batch_order_158_exclude",
        created_at=EXPORTED_AT,
    )

    assert "node_output:unrelated" not in result.packet.included_data_ids
    assert "node_output:test" not in result.packet.data_type_counts


def test_export_packet_records_failed_integrity_without_writing_external_db() -> None:
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

    result = record_graph_memory_export_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_158",
        batch_id="batch_order_158_failed_integrity",
        created_at=EXPORTED_AT,
    )

    packet = result.packet
    assert packet.graph_integrity_status == "failed"
    assert packet.graph_integrity_summary["missing_source_ref_count"] == 2
    assert packet.graph_integrity_summary["missing_edge_endpoint_count"] == 2
    assert packet.external_write_status == "not_run"


def test_export_packet_is_idempotent_for_same_batch_and_timestamp(tmp_path) -> None:
    root = _sample_repo(tmp_path)
    trace_store, data_store = _graph_and_source_store(root)

    first = record_graph_memory_export_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_158",
        batch_id="batch_order_158_idempotent",
        created_at=EXPORTED_AT,
    )
    second = record_graph_memory_export_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_158",
        batch_id="batch_order_158_idempotent",
        created_at=EXPORTED_AT,
    )

    assert first.created_data_ids == [first.packet.packet_id]
    assert second.created_data_ids == []
    assert second.existing_data_ids == [first.packet.packet_id]
    assert first.packet == second.packet


def _graph_and_source_store(root) -> tuple[TraceStore, DataStore]:
    trace_store = TraceStore()
    data_store = DataStore()
    record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_158_core",
        batch_id="batch_order_158_core",
        capsules=[_sample_capsule("turn_order_158_previous")],
    )
    record_songryeon_core_source_manifest_ingest(
        trace_store=trace_store,
        data_store=data_store,
        root_path=root,
        turn_id="turn_order_158_source",
        batch_id="batch_order_158_source",
        observed_at=OBSERVED_AT,
        ingested_at=INGESTED_AT,
    )
    return trace_store, data_store


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
