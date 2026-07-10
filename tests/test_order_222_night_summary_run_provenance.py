from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import record_graph_memory_for_capsules
from songryeon_core.core.graph_source_ingest import record_graph_source_kind_ingest
from songryeon_core.core.schemas import NodeMovement, TurnStateCapsule
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.night_summarize_source_leaf import (
    run_night_summarize_changed_source_leaves,
)
from songryeon_core.nodes.night_summarize_time_bundle import (
    run_night_summarize_time_bundle,
)
from songryeon_core.runtime.night_changed_source_summary import (
    run_night_changed_source_summary,
)
from songryeon_core.runtime.night_token_budget_layer_summary import (
    run_night_token_budget_layer_summary,
)


class _SummaryAdapter:
    model_id = "order-222-summary-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {"summary_text": "provenance test summary"}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def test_time_bundle_summary_records_night_run_provenance() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_222_time_graph",
        batch_id="batch_order_222_time_graph",
        capsules=[_sample_capsule("turn_order_222_time_previous")],
    )
    time_bundle_id = _only_data_id(data_store, "graph_memory:node:time_bundle")

    result = run_night_summarize_time_bundle(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_222_time",
        target_time_bundle_node_id=time_bundle_id,
        summary_run_id="batch_order_222_time",
        adapter=_SummaryAdapter(),
    )

    _assert_recorded_provenance(
        result.frame.__dict__,
        summary_run_id="batch_order_222_time",
        night_turn_id="turn_order_222_time",
    )
    payload = data_store.require_record(result.frame.summary_graph_node_id).payload
    assert isinstance(payload, dict)
    _assert_recorded_provenance(
        payload,
        summary_run_id="batch_order_222_time",
        night_turn_id="turn_order_222_time",
    )


def test_source_leaf_summary_records_night_run_provenance(tmp_path) -> None:
    source_path = tmp_path / "policy.md"
    source_path.write_text("policy provenance body\n", encoding="utf-8")
    trace_store = TraceStore()
    data_store = DataStore()
    record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_222_source_graph",
        batch_id="batch_order_222_source_graph",
        capsules=[_sample_capsule("turn_order_222_source_previous")],
    )
    ingest = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_222_source_ingest",
        batch_id="batch_order_222_source_ingest",
        source_paths_by_kind={"internal_document": [source_path]},
        observed_at="2026-07-09T10:00:00",
        ingested_at="2026-07-09T10:00:01",
        store_text_snapshots=True,
    )

    batch = run_night_summarize_changed_source_leaves(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_222_source",
        source_observation_ledger_frame_id=ingest.source_observation_ledger_frame_id,
        summary_run_id="batch_order_222_source",
        adapter=_SummaryAdapter(),
    )

    assert len(batch.results) == 1
    frame = batch.results[0].frame
    _assert_recorded_provenance(
        frame.__dict__,
        summary_run_id="batch_order_222_source",
        night_turn_id="turn_order_222_source",
    )
    payload = data_store.require_record(frame.summary_graph_node_id).payload
    assert isinstance(payload, dict)
    _assert_recorded_provenance(
        payload,
        summary_run_id="batch_order_222_source",
        night_turn_id="turn_order_222_source",
    )


def test_token_budget_bundle_summary_records_night_run_provenance(tmp_path) -> None:
    root = _minimal_project_root(tmp_path / "project")
    store_dir = tmp_path / "store"
    run_night_changed_source_summary(
        root_path=root,
        store_dir=store_dir,
        batch_id="batch_order_222_sources",
        turn_id="turn_order_222_sources",
        llm_mode="fake",
    )

    run_night_token_budget_layer_summary(
        store_dir=store_dir,
        batch_id="batch_order_222_token",
        turn_id="turn_order_222_token",
        max_bundle_chars=90,
        llm_mode="fake",
    )

    data_store = DataStore.load_json(store_dir / "data_store.json")
    token_summary_payloads = [
        record.payload
        for record in data_store.list_records()
        if record.data_type == "graph_memory:node:summary"
        and isinstance(record.payload, dict)
        and record.payload.get("data_kind") == "token_budget_bundle_summary"
    ]
    assert token_summary_payloads
    _assert_recorded_provenance(
        token_summary_payloads[0],
        summary_run_id="batch_order_222_token",
        night_turn_id="turn_order_222_token",
    )


def _assert_recorded_provenance(
    payload: dict[str, object],
    *,
    summary_run_id: str,
    night_turn_id: str,
) -> None:
    assert payload["summary_run_id"] == summary_run_id
    assert payload["night_turn_id"] == night_turn_id
    assert payload["night_batch_id"] == summary_run_id
    assert isinstance(payload["summary_created_at"], str)
    assert payload["summary_created_at"]
    assert payload["run_provenance_status"] == "recorded"


def _only_data_id(data_store: DataStore, data_type: str) -> str:
    records = [record for record in data_store.list_records() if record.data_type == data_type]
    assert len(records) == 1
    return records[0].data_id


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


def _minimal_project_root(root) -> object:
    root.mkdir(parents=True)
    (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (root / "README.md").write_text("# Readme\n", encoding="utf-8")
    (root / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
    docs = root / "Administrative_Reform_1" / "04_Orders"
    docs.mkdir(parents=True)
    (docs / "ORDER_TEST.md").write_text("# Test order\n", encoding="utf-8")
    return root

