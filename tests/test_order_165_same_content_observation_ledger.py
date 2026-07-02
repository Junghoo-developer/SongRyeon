from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import record_graph_memory_for_capsules
from songryeon_core.core.graph_source_ingest import record_graph_source_kind_ingest
from songryeon_core.core.schemas import (
    NodeMovement,
    SourceObservationLedgerFrame,
    SourceVersionLineageFrame,
    TurnStateCapsule,
    validate_source_observation_ledger_frame,
    validate_source_version_lineage_frame,
)
from songryeon_core.core.source_version_lineage import (
    SOURCE_OBSERVATION_LEDGER_FRAME_DATA_TYPE,
)
from songryeon_core.core.trace_store import TraceStore


def test_same_content_reobserve_does_not_create_new_raw_source_version(tmp_path) -> None:
    source = tmp_path / "unchanged_code.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    trace_store, data_store = _core_time_axis_store()

    first = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_165",
        batch_id="batch_order_165_001",
        source_paths_by_kind={"source_code_file": [source]},
        observed_at="2026-07-02T15:00:00",
        ingested_at="2026-07-02T15:00:01",
    )
    second = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_165",
        batch_id="batch_order_165_002",
        source_paths_by_kind={"source_code_file": [source]},
        observed_at="2026-07-02T16:00:00",
        ingested_at="2026-07-02T16:00:01",
    )

    assert first.raw_source_node_ids == second.raw_source_node_ids
    assert first.source_file_data_ids != second.source_file_data_ids
    assert second.source_observation_status_counts == {"unchanged": 1}

    raw_source_records = [
        record
        for record in data_store.list_records()
        if record.data_type == "graph_memory:node:raw_source"
    ]
    assert len(raw_source_records) == 1

    lineage = SourceVersionLineageFrame(
        **data_store.require_record(second.source_version_lineage_frame_ids[0]).payload
    )
    validate_source_version_lineage_frame(lineage)
    assert lineage.lineage_status == "single_version"
    assert lineage.version_source_graph_node_ids == first.raw_source_node_ids

    observation_record = data_store.require_record(second.source_observation_ledger_frame_id)
    assert observation_record.data_type == SOURCE_OBSERVATION_LEDGER_FRAME_DATA_TYPE
    observation = SourceObservationLedgerFrame(**observation_record.payload)
    validate_source_observation_ledger_frame(observation)
    assert observation.ledger_status == "recorded"
    assert observation.observation_records[0]["observation_status"] == "unchanged"
    assert observation.observation_records[0]["previous_active_source_graph_node_id"] == (
        first.raw_source_node_ids[0]
    )


def test_content_change_creates_new_raw_source_version_and_observation_record(tmp_path) -> None:
    source = tmp_path / "changing_code.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    trace_store, data_store = _core_time_axis_store()

    first = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_165",
        batch_id="batch_order_165_change_001",
        source_paths_by_kind={"source_code_file": [source]},
        observed_at="2026-07-02T17:00:00",
        ingested_at="2026-07-02T17:00:01",
    )
    source.write_text("VALUE = 2\n", encoding="utf-8")
    second = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_165",
        batch_id="batch_order_165_change_002",
        source_paths_by_kind={"source_code_file": [source]},
        observed_at="2026-07-02T18:00:00",
        ingested_at="2026-07-02T18:00:01",
    )

    assert first.raw_source_node_ids != second.raw_source_node_ids
    assert second.source_observation_status_counts == {"content_changed": 1}

    lineage = SourceVersionLineageFrame(
        **data_store.require_record(second.source_version_lineage_frame_ids[0]).payload
    )
    validate_source_version_lineage_frame(lineage)
    assert lineage.lineage_status == "content_changed"
    assert lineage.version_source_graph_node_ids == [
        first.raw_source_node_ids[0],
        second.raw_source_node_ids[0],
    ]
    assert lineage.superseded_source_graph_node_ids == [first.raw_source_node_ids[0]]


def _core_time_axis_store() -> tuple[TraceStore, DataStore]:
    trace_store = TraceStore()
    data_store = DataStore()
    record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_165_core",
        batch_id="batch_order_165_core",
        capsules=[_sample_capsule()],
    )
    return trace_store, data_store


def _sample_capsule(turn_id: str = "turn_order_165_previous") -> TurnStateCapsule:
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
