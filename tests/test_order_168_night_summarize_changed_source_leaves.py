from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import record_graph_memory_for_capsules
from songryeon_core.core.graph_memory_export import record_graph_memory_export_packet
from songryeon_core.core.graph_source_ingest import record_graph_source_kind_ingest
from songryeon_core.core.graph_vessel_adapter import record_graph_vessel_write_plan
from songryeon_core.core.schemas import (
    NightSourceLeafSummaryFrame,
    NodeMovement,
    TurnStateCapsule,
    validate_night_source_leaf_summary_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.night_summarize_source_leaf import (
    NIGHT_SUMMARIZE_SOURCE_LEAF_FRAME_DATA_TYPE,
    run_night_summarize_changed_source_leaves,
)


class SourceSummaryAdapter:
    model_id = "order-168-source-summary-adapter"

    def __init__(self) -> None:
        self.input_payloads: list[dict[str, object]] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.input_payloads.append(request.input_payload)
        source_text = str(request.input_payload.get("source_text") or "")
        payload = {
            "summary_text": f"Source leaf summary: {source_text.strip()[:40]}",
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def test_new_source_versions_are_all_summarized_one_to_one(tmp_path) -> None:
    source_a = tmp_path / "policy_a.md"
    source_b = tmp_path / "tool_b.py"
    source_a.write_text("policy alpha\n", encoding="utf-8")
    source_b.write_text("VALUE = 'beta'\n", encoding="utf-8")
    trace_store, data_store = _core_time_axis_store()
    ingest = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_ingest",
        batch_id="batch_order_168_new",
        source_paths_by_kind={
            "internal_document": [source_a],
            "source_code_file": [source_b],
        },
        observed_at="2026-07-02T20:00:00",
        ingested_at="2026-07-02T20:00:01",
        store_text_snapshots=True,
    )
    adapter = SourceSummaryAdapter()

    batch = run_night_summarize_changed_source_leaves(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_summary",
        source_observation_ledger_frame_id=ingest.source_observation_ledger_frame_id,
        summary_run_id="001",
        adapter=adapter,
    )

    assert batch.selected_source_graph_node_ids == ingest.raw_source_node_ids
    assert len(batch.results) == 2
    assert len(adapter.input_payloads) == 2
    for result in batch.results:
        frame = result.frame
        validate_night_source_leaf_summary_frame(frame)
        assert frame.summary_status == "ran"
        assert frame.info_class == "relative"
        assert frame.source_mode == "single_source"
        assert frame.claim_alignment == "single_absolute_record"
        assert frame.source_graph_node_ids == [frame.target_graph_node_id]
        assert frame.generated_by == (
            f"LLM:{adapter.model_id}:night_summarize_source_leaf"
        )
        assert result.summary_graph_node_data_id == frame.summary_graph_node_id
        assert result.summary_edge_data_id is not None
        summary_record = data_store.require_record(frame.summary_graph_node_id)
        assert summary_record.data_type == "graph_memory:node:summary"
        assert summary_record.payload["target_node_kind"] == "raw_source"
        edge_record = data_store.require_record(result.summary_edge_data_id)
        assert edge_record.data_type == "graph_memory:edge:SUMMARY_OF"
        assert edge_record.payload["from_node_id"] == frame.summary_graph_node_id
        assert edge_record.payload["to_node_id"] == frame.target_graph_node_id


def test_unchanged_observation_is_not_summarized(tmp_path) -> None:
    source = tmp_path / "unchanged.md"
    source.write_text("same content\n", encoding="utf-8")
    trace_store, data_store = _core_time_axis_store()
    record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_ingest",
        batch_id="batch_order_168_unchanged_001",
        source_paths_by_kind={"internal_document": [source]},
        observed_at="2026-07-02T21:00:00",
        ingested_at="2026-07-02T21:00:01",
        store_text_snapshots=True,
    )
    second = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_ingest",
        batch_id="batch_order_168_unchanged_002",
        source_paths_by_kind={"internal_document": [source]},
        observed_at="2026-07-02T22:00:00",
        ingested_at="2026-07-02T22:00:01",
        store_text_snapshots=True,
    )
    adapter = SourceSummaryAdapter()

    batch = run_night_summarize_changed_source_leaves(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_summary",
        source_observation_ledger_frame_id=second.source_observation_ledger_frame_id,
        summary_run_id="001",
        adapter=adapter,
    )

    assert batch.selected_source_graph_node_ids == []
    assert batch.skipped_unchanged_source_graph_node_ids == second.raw_source_node_ids
    assert batch.results == []
    assert adapter.input_payloads == []
    assert _summary_record_count(data_store) == 0


def test_changed_source_version_summarizes_only_new_active_leaf(tmp_path) -> None:
    source = tmp_path / "changing.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    trace_store, data_store = _core_time_axis_store()
    first = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_ingest",
        batch_id="batch_order_168_change_001",
        source_paths_by_kind={"source_code_file": [source]},
        observed_at="2026-07-02T23:00:00",
        ingested_at="2026-07-02T23:00:01",
        store_text_snapshots=True,
    )
    source.write_text("VALUE = 2\n", encoding="utf-8")
    second = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_ingest",
        batch_id="batch_order_168_change_002",
        source_paths_by_kind={"source_code_file": [source]},
        observed_at="2026-07-03T00:00:00",
        ingested_at="2026-07-03T00:00:01",
        store_text_snapshots=True,
    )

    batch = run_night_summarize_changed_source_leaves(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_summary",
        source_observation_ledger_frame_id=second.source_observation_ledger_frame_id,
        summary_run_id="001",
        adapter=SourceSummaryAdapter(),
    )

    assert batch.selected_source_graph_node_ids == [second.raw_source_node_ids[0]]
    assert batch.results[0].frame.target_graph_node_id == second.raw_source_node_ids[0]
    assert batch.results[0].frame.target_graph_node_id != first.raw_source_node_ids[0]
    assert _summary_record_count(data_store) == 1


def test_missing_text_snapshot_records_skipped_without_summary_graph_node(tmp_path) -> None:
    source = tmp_path / "metadata_only.md"
    source.write_text("text exists but snapshot disabled\n", encoding="utf-8")
    trace_store, data_store = _core_time_axis_store()
    ingest = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_ingest",
        batch_id="batch_order_168_no_snapshot",
        source_paths_by_kind={"internal_document": [source]},
        observed_at="2026-07-03T01:00:00",
        ingested_at="2026-07-03T01:00:01",
        store_text_snapshots=False,
    )

    batch = run_night_summarize_changed_source_leaves(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_summary",
        source_observation_ledger_frame_id=ingest.source_observation_ledger_frame_id,
        summary_run_id="001",
        adapter=SourceSummaryAdapter(),
    )

    frame = batch.results[0].frame
    assert frame.summary_status == "skipped_no_text_snapshot"
    assert frame.info_class == "absolute"
    assert frame.semantic_judgement_status == "not_run"
    assert batch.results[0].summary_graph_node_data_id is None
    assert data_store.get_record(frame.summary_graph_node_id) is None
    assert data_store.require_record(frame.frame_id).data_type == (
        NIGHT_SUMMARIZE_SOURCE_LEAF_FRAME_DATA_TYPE
    )
    assert _summary_record_count(data_store) == 0


def test_empty_text_snapshot_records_skipped_empty_text(tmp_path) -> None:
    source = tmp_path / "empty.md"
    source.write_text("", encoding="utf-8")
    trace_store, data_store = _core_time_axis_store()
    ingest = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_ingest",
        batch_id="batch_order_168_empty",
        source_paths_by_kind={"internal_document": [source]},
        observed_at="2026-07-03T02:00:00",
        ingested_at="2026-07-03T02:00:01",
        store_text_snapshots=True,
    )

    batch = run_night_summarize_changed_source_leaves(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_summary",
        source_observation_ledger_frame_id=ingest.source_observation_ledger_frame_id,
        summary_run_id="001",
        adapter=SourceSummaryAdapter(),
    )

    frame = batch.results[0].frame
    assert frame.summary_status == "skipped_empty_text"
    assert frame.failure_type == "empty_text"
    assert frame.text_snapshot_data_id is not None
    assert batch.results[0].summary_graph_node_data_id is None
    assert _summary_record_count(data_store) == 0


def test_source_leaf_summary_node_and_edge_are_exported_and_planned(tmp_path) -> None:
    source = tmp_path / "export_me.md"
    source.write_text("exported source text\n", encoding="utf-8")
    trace_store, data_store = _core_time_axis_store()
    ingest = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_ingest",
        batch_id="batch_order_168_export_source",
        source_paths_by_kind={"internal_document": [source]},
        observed_at="2026-07-03T03:00:00",
        ingested_at="2026-07-03T03:00:01",
        store_text_snapshots=True,
    )
    batch = run_night_summarize_changed_source_leaves(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_summary",
        source_observation_ledger_frame_id=ingest.source_observation_ledger_frame_id,
        summary_run_id="001",
        adapter=SourceSummaryAdapter(),
    )
    result = batch.results[0]

    export = record_graph_memory_export_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_export",
        batch_id="batch_order_168_export",
    )
    assert result.summary_graph_node_data_id in export.packet.graph_node_data_ids
    assert result.summary_edge_data_id in export.packet.graph_edge_data_ids

    plan = record_graph_vessel_write_plan(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_plan",
        export_packet_id=export.packet.packet_id,
    )
    operations_by_source = {
        operation.source_data_id: operation.operation_kind
        for operation in plan.plan.operations
    }
    assert operations_by_source[result.summary_graph_node_data_id or ""] == (
        "upsert_graph_node"
    )
    assert operations_by_source[result.summary_edge_data_id or ""] == (
        "upsert_graph_edge"
    )


def _summary_record_count(data_store: DataStore) -> int:
    return len(
        [
            record
            for record in data_store.list_records()
            if record.data_type == "graph_memory:node:summary"
        ]
    )


def _core_time_axis_store() -> tuple[TraceStore, DataStore]:
    trace_store = TraceStore()
    data_store = DataStore()
    record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_168_core",
        batch_id="batch_order_168_core",
        capsules=[_sample_capsule()],
    )
    return trace_store, data_store


def _sample_capsule(turn_id: str = "turn_order_168_previous") -> TurnStateCapsule:
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
