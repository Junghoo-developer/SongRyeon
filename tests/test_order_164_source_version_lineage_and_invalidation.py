from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import record_graph_memory_for_capsules
from songryeon_core.core.graph_memory_export import record_graph_memory_export_packet
from songryeon_core.core.graph_source_ingest import record_graph_source_kind_ingest
from songryeon_core.core.graph_vessel_adapter import record_graph_vessel_write_plan
from songryeon_core.core.schemas import (
    NodeMovement,
    SourceVersionLineageFrame,
    SourceObservationLedgerFrame,
    SummaryInvalidationLedgerFrame,
    TurnStateCapsule,
    validate_source_observation_ledger_frame,
    validate_source_version_lineage_frame,
    validate_summary_invalidation_ledger_frame,
)
from songryeon_core.core.source_version_lineage import (
    SOURCE_OBSERVATION_LEDGER_FRAME_DATA_TYPE,
    SOURCE_VERSION_LINEAGE_FRAME_DATA_TYPE,
    SUMMARY_INVALIDATION_LEDGER_FRAME_DATA_TYPE,
)
from songryeon_core.core.trace_store import TraceStore


def test_changed_source_builds_lineage_and_invalidates_old_summary(tmp_path) -> None:
    source = tmp_path / "dynamic_policy.md"
    source.write_text("version one\n", encoding="utf-8")
    trace_store, data_store = _core_time_axis_store()

    first = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_164_source",
        batch_id="batch_order_164_source_001",
        source_paths_by_kind={"internal_document": [source]},
        observed_at="2026-07-02T10:00:00",
        ingested_at="2026-07-02T10:00:01",
    )
    _record_fake_summary_for_source(
        data_store=data_store,
        summary_node_id="graph:summary:order_164:old",
        source_graph_node_id=first.raw_source_node_ids[0],
    )

    source.write_text("version two\n", encoding="utf-8")
    second = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_164_source",
        batch_id="batch_order_164_source_002",
        source_paths_by_kind={"internal_document": [source]},
        observed_at="2026-07-02T11:00:00",
        ingested_at="2026-07-02T11:00:01",
    )

    lineage_record = data_store.require_record(second.source_version_lineage_frame_ids[0])
    assert lineage_record.data_type == SOURCE_VERSION_LINEAGE_FRAME_DATA_TYPE
    lineage = SourceVersionLineageFrame(**lineage_record.payload)
    validate_source_version_lineage_frame(lineage)
    assert lineage.source_identity_key
    assert lineage.lineage_status == "content_changed"
    assert lineage.version_source_graph_node_ids == [
        first.raw_source_node_ids[0],
        second.raw_source_node_ids[0],
    ]
    assert lineage.active_source_graph_node_id == second.raw_source_node_ids[0]
    assert lineage.superseded_source_graph_node_ids == [first.raw_source_node_ids[0]]
    assert len(set(lineage.content_sha1_by_version.values())) == 2

    ledger_record = data_store.require_record(second.summary_invalidation_ledger_frame_id)
    assert ledger_record.data_type == SUMMARY_INVALIDATION_LEDGER_FRAME_DATA_TYPE
    ledger = SummaryInvalidationLedgerFrame(**ledger_record.payload)
    validate_summary_invalidation_ledger_frame(ledger)
    assert ledger.ledger_status == "invalidations_recorded"
    assert ledger.invalidated_summary_node_ids == ["graph:summary:order_164:old"]
    assert ledger.invalidation_records[0]["invalidated_reason_code"] == (
        "source_content_changed"
    )
    assert ledger.invalidation_records[0]["validity_status"] == (
        "invalidated_by_source_change"
    )
    assert ledger.invalidation_records[0]["superseded_source_graph_node_id"] == (
        first.raw_source_node_ids[0]
    )
    assert ledger.invalidation_records[0]["superseding_source_graph_node_id"] == (
        second.raw_source_node_ids[0]
    )


def test_same_content_reobserve_reuses_raw_source_and_keeps_summary_ledger_empty(tmp_path) -> None:
    source = tmp_path / "stable_policy.md"
    source.write_text("same content\n", encoding="utf-8")
    trace_store, data_store = _core_time_axis_store()

    first = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_164_source",
        batch_id="batch_order_164_same_001",
        source_paths_by_kind={"internal_document": [source]},
        observed_at="2026-07-02T12:00:00",
        ingested_at="2026-07-02T12:00:01",
    )
    _record_fake_summary_for_source(
        data_store=data_store,
        summary_node_id="graph:summary:order_164:same",
        source_graph_node_id=first.raw_source_node_ids[0],
    )
    second = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_164_source",
        batch_id="batch_order_164_same_002",
        source_paths_by_kind={"internal_document": [source]},
        observed_at="2026-07-02T13:00:00",
        ingested_at="2026-07-02T13:00:01",
    )

    lineage = SourceVersionLineageFrame(
        **data_store.require_record(second.source_version_lineage_frame_ids[0]).payload
    )
    assert first.raw_source_node_ids == second.raw_source_node_ids
    assert lineage.lineage_status == "single_version"
    assert lineage.version_source_graph_node_ids == [first.raw_source_node_ids[0]]

    observation_record = data_store.require_record(
        second.source_observation_ledger_frame_id
    )
    assert observation_record.data_type == SOURCE_OBSERVATION_LEDGER_FRAME_DATA_TYPE
    observation = SourceObservationLedgerFrame(**observation_record.payload)
    validate_source_observation_ledger_frame(observation)
    assert observation.observation_status_counts == {"unchanged": 1}
    assert observation.observation_records[0]["active_source_graph_node_id"] == (
        first.raw_source_node_ids[0]
    )

    ledger = SummaryInvalidationLedgerFrame(
        **data_store.require_record(second.summary_invalidation_ledger_frame_id).payload
    )
    validate_summary_invalidation_ledger_frame(ledger)
    assert ledger.ledger_status == "no_invalidations"
    assert ledger.invalidated_summary_node_ids == []
    assert ledger.invalidation_records == []


def test_lineage_and_invalidation_ledgers_are_exported_as_support_records(tmp_path) -> None:
    source = tmp_path / "exported_policy.md"
    source.write_text("export me\n", encoding="utf-8")
    trace_store, data_store = _core_time_axis_store()

    ingest = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_164_source",
        batch_id="batch_order_164_export_source",
        source_paths_by_kind={"internal_document": [source]},
        observed_at="2026-07-02T14:00:00",
        ingested_at="2026-07-02T14:00:01",
    )
    export = record_graph_memory_export_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_164_export",
        batch_id="batch_order_164_export",
        created_at="2026-07-02T14:00:02",
    )

    assert ingest.source_version_lineage_frame_ids[0] in (
        export.packet.source_version_lineage_frame_data_ids
    )
    assert ingest.source_observation_ledger_frame_id in (
        export.packet.source_observation_ledger_frame_data_ids
    )
    assert ingest.summary_invalidation_ledger_frame_id in (
        export.packet.summary_invalidation_ledger_frame_data_ids
    )

    plan = record_graph_vessel_write_plan(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_164_plan",
        export_packet_id=export.packet.packet_id,
        created_at="2026-07-02T14:00:03",
    )
    support_ids = {
        operation.source_data_id
        for operation in plan.plan.operations
        if operation.operation_kind == "upsert_support_record"
    }
    assert ingest.source_version_lineage_frame_ids[0] in support_ids
    assert ingest.source_observation_ledger_frame_id in support_ids
    assert ingest.summary_invalidation_ledger_frame_id in support_ids


def _record_fake_summary_for_source(
    *,
    data_store: DataStore,
    summary_node_id: str,
    source_graph_node_id: str,
) -> None:
    data_store.create_record(
        data_id=summary_node_id,
        data_type="graph_memory:node:summary",
        exists=True,
        created_at="2026-07-02T10:30:00",
        source_trace_id="trace:order_164:summary",
        payload={
            "node_id": summary_node_id,
            "node_kind": "summary",
            "source_graph_node_ids": [source_graph_node_id],
            "source_data_ids": [source_graph_node_id],
            "generated_by": "LLM:test:summary",
            "info_class": "mixed",
            "semantic_judgement_status": "ran",
        },
    )


def _core_time_axis_store() -> tuple[TraceStore, DataStore]:
    trace_store = TraceStore()
    data_store = DataStore()
    record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_164_core",
        batch_id="batch_order_164_core",
        capsules=[_sample_capsule()],
    )
    return trace_store, data_store


def _sample_capsule(turn_id: str = "turn_order_164_previous") -> TurnStateCapsule:
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
