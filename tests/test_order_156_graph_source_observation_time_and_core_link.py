from __future__ import annotations

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import (
    TIME_AXIS_NODE_ID,
    record_graph_memory_for_capsules,
)
from songryeon_core.core.graph_memory_integrity import audit_graph_memory_integrity
from songryeon_core.core.graph_source_ingest import (
    graph_source_ingest_snapshot_id,
    record_graph_source_kind_ingest,
    source_ingest_time_bundle_graph_node_id,
)
from songryeon_core.core.schemas import NodeMovement, TurnStateCapsule
from songryeon_core.core.trace_store import TraceStore


OBSERVED_AT = "2026-07-01T13:00:00"
INGESTED_AT = "2026-07-01T13:00:01"


def test_source_ingest_records_observation_time_on_file_and_graph_node(tmp_path) -> None:
    source = tmp_path / "changing_policy.md"
    source.write_text("version one\n", encoding="utf-8")
    trace_store, data_store = _core_time_axis_store()

    result = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_156",
        batch_id="batch_order_156",
        source_paths_by_kind={"internal_document": [source]},
        observed_at=OBSERVED_AT,
        ingested_at=INGESTED_AT,
    )

    file_record = data_store.require_record(result.source_file_data_ids[0])
    raw_record = data_store.require_record(result.raw_source_node_ids[0])
    assert isinstance(file_record.payload, dict)
    assert isinstance(raw_record.payload, dict)

    for payload in (file_record.payload, raw_record.payload):
        assert payload["observed_at"] == OBSERVED_AT
        assert payload["ingested_at"] == INGESTED_AT
        assert payload["source_last_modified_at"]
        assert payload["exists_at_ingest"] is True
        assert payload["content_sha1"]

    assert raw_record.payload["node_kind"] == "raw_source"
    assert raw_record.payload["semantic_judgement_status"] == "not_run"
    assert raw_record.payload["info_class"] == "absolute"


def test_source_kind_bundles_are_linked_under_core_ego_time_axis(tmp_path) -> None:
    internal_doc = tmp_path / "doc.md"
    code_file = tmp_path / "tool.py"
    internal_doc.write_text("doc material\n", encoding="utf-8")
    code_file.write_text("print('tool')\n", encoding="utf-8")
    trace_store, data_store = _core_time_axis_store()

    result = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_156",
        batch_id="batch_order_156_link",
        source_paths_by_kind={
            "internal_document": [internal_doc],
            "source_code_file": [code_file],
        },
        observed_at=OBSERVED_AT,
        ingested_at=INGESTED_AT,
    )

    source_ingest_node = data_store.require_record(
        result.source_ingest_time_bundle_node_id
    )
    assert source_ingest_node.payload["node_kind"] == "source_ingest_time_bundle"
    assert source_ingest_node.payload["source_graph_node_ids"] == result.source_kind_bundle_node_ids

    edge_records = [
        record
        for record in data_store.list_records()
        if record.data_type.startswith("graph_memory:edge:")
    ]
    edge_pairs = {
        (record.payload["edge_kind"], record.payload["from_node_id"], record.payload["to_node_id"])
        for record in edge_records
    }
    assert (
        "CHILD_OF_TIME_AXIS",
        TIME_AXIS_NODE_ID,
        result.source_ingest_time_bundle_node_id,
    ) in edge_pairs
    for bundle_id in result.source_kind_bundle_node_ids:
        assert ("CONTAINS", result.source_ingest_time_bundle_node_id, bundle_id) in edge_pairs

    report = audit_graph_memory_integrity(data_store)
    assert report.passed, report.to_summary()


def test_source_ingest_creates_source_snapshot_and_rloop_guide(tmp_path) -> None:
    source = tmp_path / "guide.md"
    source.write_text("guide me\n", encoding="utf-8")
    trace_store, data_store = _core_time_axis_store()

    result = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_156",
        batch_id="batch_order_156_guide",
        source_paths_by_kind={"internal_document": [source]},
        observed_at=OBSERVED_AT,
        ingested_at=INGESTED_AT,
    )

    snapshot = data_store.require_record(result.graph_snapshot_id)
    guide = data_store.require_record(result.rloop_graph_guide_packet_id)
    assert result.graph_snapshot_id == graph_source_ingest_snapshot_id("batch_order_156_guide")
    assert snapshot.payload["root_node_id"] == "graph:core_ego:root"
    assert snapshot.payload["time_axis_node_id"] == TIME_AXIS_NODE_ID
    assert snapshot.payload["node_kind_counts"]["source_ingest_time_bundle"] == 1
    assert snapshot.payload["node_kind_counts"]["source_kind_bundle"] == 1
    assert snapshot.payload["node_kind_counts"]["raw_source"] == 1
    assert result.source_ingest_time_bundle_node_id in snapshot.payload["graph_node_ids"]

    assert guide.payload["graph_snapshot_id"] == result.graph_snapshot_id
    assert guide.payload["available_entry_nodes"] == [TIME_AXIS_NODE_ID]
    assert guide.payload["recommended_traversal_hints_status"] == "not_run"
    assert guide.payload["semantic_judgement_status"] == "not_run"


def test_source_ingest_requires_existing_core_ego_time_axis(tmp_path) -> None:
    source = tmp_path / "orphan.md"
    source.write_text("orphan source\n", encoding="utf-8")

    with pytest.raises(ValueError, match="requires existing CoreEgo time axis"):
        record_graph_source_kind_ingest(
            trace_store=TraceStore(),
            data_store=DataStore(),
            turn_id="turn_order_156",
            batch_id="batch_order_156_orphan",
            source_paths_by_kind={"internal_document": [source]},
            observed_at=OBSERVED_AT,
            ingested_at=INGESTED_AT,
        )


def test_same_file_same_content_check_reuses_raw_source_snapshot(tmp_path) -> None:
    source = tmp_path / "same_content.md"
    source.write_text("same content\n", encoding="utf-8")
    trace_store, data_store = _core_time_axis_store()

    first = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_156",
        batch_id="batch_order_156_obs_001",
        source_paths_by_kind={"internal_document": [source]},
        observed_at="2026-07-01T14:00:00",
        ingested_at="2026-07-01T14:00:01",
    )
    second = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_156",
        batch_id="batch_order_156_obs_002",
        source_paths_by_kind={"internal_document": [source]},
        observed_at="2026-07-01T15:00:00",
        ingested_at="2026-07-01T15:00:01",
    )

    assert first.raw_source_node_ids == second.raw_source_node_ids
    assert first.source_file_data_ids != second.source_file_data_ids
    assert (
        data_store.require_record(first.raw_source_node_ids[0]).payload["content_sha1"]
        == data_store.require_record(second.raw_source_node_ids[0]).payload["content_sha1"]
    )
    assert second.source_observation_status_counts == {"unchanged": 1}


def _core_time_axis_store() -> tuple[TraceStore, DataStore]:
    trace_store = TraceStore()
    data_store = DataStore()
    record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_156_core",
        batch_id="batch_order_156_core",
        capsules=[_sample_capsule()],
    )
    return trace_store, data_store


def _sample_capsule(turn_id: str = "turn_order_156_previous") -> TurnStateCapsule:
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
