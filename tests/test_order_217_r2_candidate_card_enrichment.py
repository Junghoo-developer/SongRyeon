from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import (
    record_r_loop_vessel_read_packet,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_one_step import run_r_loop_vessel_traverse

from tests.test_order_175_vessel_backed_r_read_packet import (
    READ_AT,
    FakeRLoopVesselDriverFactory,
    _config,
)
from tests.test_order_184_r_vessel_multi_step_traversal import SOURCE_KIND_ID
from tests.test_order_190_r_vessel_token_summary_deeper_child_expansion import (
    TokenSummaryNeedsDeeperAdapter,
    _entry_rows,
    _summary_rows,
)


def test_r2_candidate_cards_include_child_structure_without_child_text() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_217_packet",
        batch_id="order_217_packet",
        config=_config(),
        created_at=READ_AT,
        limit=2,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows(),
            summary_rows=_summary_rows(),
        ),
    )
    adapter = CapturingCandidateCardAdapter()

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_217_traverse",
        user_question="R2 후보 카드 구조 보강을 확인해",
        read_packet=recorded.packet,
        adapter=adapter,
        frame_label="order_217_traverse",
        input_ref=[recorded.trace_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert len(adapter.r2_payloads) >= 3

    first_step_records = _candidate_records(adapter.r2_payloads[0])
    time_axis = _record_by_candidate_kind(first_step_records, "time_axis")
    assert time_axis["child_candidate_visibility"] == (
        "structure_counts_and_clean_summary_layer_preview"
    )
    assert time_axis["child_candidate_count"] == 2
    assert time_axis["child_candidate_kind_counts"] == {
        "source_ingest_bundle": 1,
        "time_bundle": 1,
    }
    assert time_axis["has_child_candidates"] is True

    second_step_records = _candidate_records(adapter.r2_payloads[1])
    source_ingest = _record_by_candidate_kind(
        second_step_records,
        "source_ingest_bundle",
    )
    assert source_ingest["child_candidate_kind_counts"] == {
        "source_kind_bundle": 1,
    }
    assert source_ingest["child_branch_role_counts"] == {
        "source_material_ingest": 1,
    }

    third_step_records = _candidate_records(adapter.r2_payloads[2])
    source_kind = _record_by_node_ref_target(
        third_step_records,
        expected_candidate_kind="source_kind_bundle",
    )
    assert source_kind["candidate_kind"] == "source_kind_bundle"
    assert source_kind["child_candidate_kind_counts"] == {"summary": 2}
    assert source_kind["child_data_kind_counts"] == {
        "token_budget_bundle_summary": 2,
    }
    assert source_kind["has_summary_child_candidate"] is True
    assert source_kind["has_token_summary_child"] is True

    for payload in adapter.r2_payloads:
        for record in _candidate_records(payload):
            assert "summary_text" not in record


def test_r2_candidate_card_enrichment_is_visible_for_source_kind_node() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_217_source_kind_packet",
        batch_id="order_217_source_kind_packet",
        config=_config(),
        created_at=READ_AT,
        limit=2,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows(),
            summary_rows=_summary_rows(),
        ),
    )
    adapter = CapturingCandidateCardAdapter()

    run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_217_source_kind",
        user_question="source kind 아래 token summary 후보 구조를 확인해",
        read_packet=recorded.packet,
        adapter=adapter,
        frame_label="order_217_source_kind",
        input_ref=[recorded.trace_event_id],
    )

    matching_records = [
        record
        for payload in adapter.r2_payloads
        for record in _candidate_records(payload)
        if record.get("candidate_kind") == "source_kind_bundle"
    ]
    assert matching_records
    assert any(record["has_token_summary_child"] for record in matching_records)
    assert any(record["child_summary_depths"] == [2, 3] for record in matching_records)


def test_r2_repair_payload_preserves_valid_failed_selection_refs() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_217_repair_packet",
        batch_id="order_217_repair_packet",
        config=_config(),
        created_at=READ_AT,
        limit=2,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows(),
            summary_rows=_summary_rows(),
        ),
    )
    adapter = ValidSelectionInvalidGranularityAdapter()

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_217_repair",
        user_question="R2 선택 번호표는 보존하고 enum만 수리해",
        read_packet=recorded.packet,
        adapter=adapter,
        frame_label="order_217_repair",
        input_ref=[recorded.trace_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.r2_selections[0].selected_graph_node_id == "graph:axis:time"
    assert adapter.preserve_failed_selection_status == "valid_selected_refs"
    assert adapter.repaired_surface_ref == adapter.failed_surface_ref
    assert adapter.repaired_node_ref == adapter.failed_node_ref


class CapturingCandidateCardAdapter(TokenSummaryNeedsDeeperAdapter):
    def __init__(self) -> None:
        self.r2_payloads: list[dict[str, object]] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R2 Vessel Node Selector" in request.prompt:
            self.r2_payloads.append(dict(request.input_payload))
        return super().complete(request)


class ValidSelectionInvalidGranularityAdapter(TokenSummaryNeedsDeeperAdapter):
    def __init__(self) -> None:
        self.failed_once = False
        self.failed_surface_ref: str | None = None
        self.failed_node_ref: str | None = None
        self.repaired_surface_ref: str | None = None
        self.repaired_node_ref: str | None = None
        self.preserve_failed_selection_status: str | None = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R2 Vessel Node Selector" not in request.prompt:
            return super().complete(request)
        if not self.failed_once and "schema_repair_request" not in request.input_payload:
            self.failed_once = True
            surface_ref, node_ref = _first_surface_and_node_ref(request.input_payload)
            self.failed_surface_ref = surface_ref
            self.failed_node_ref = node_ref
            payload = {
                "selection_status": "selected",
                "selected_surface_ref": surface_ref,
                "selected_node_ref": node_ref,
                "selection_reason": "Valid refs, invalid granularity for repair test.",
                "expected_information_granularity": "낮은 요약",
                "expected_source_kind": "time_axis",
            }
            return LLMResponse(
                text=json.dumps(payload, ensure_ascii=False),
                model_id=self.model_id,
                raw=payload,
            )
        if "schema_repair_request" in request.input_payload:
            preserve = request.input_payload["r2_copy_repair_table"][
                "preserve_failed_selection_refs"
            ]
            self.preserve_failed_selection_status = preserve["status"]
            self.repaired_surface_ref = preserve["selected_surface_ref"]
            self.repaired_node_ref = preserve["selected_node_ref"]
            payload = {
                "selection_status": "selected",
                "selected_surface_ref": self.repaired_surface_ref,
                "selected_node_ref": self.repaired_node_ref,
                "selection_reason": "Repair preserved valid refs and fixed enum.",
                "expected_information_granularity": "low_summary",
                "expected_source_kind": "time_axis",
            }
            return LLMResponse(
                text=json.dumps(payload, ensure_ascii=False),
                model_id=self.model_id,
                raw=payload,
            )
        return super().complete(request)


def _candidate_records(payload: dict[str, object]) -> list[dict[str, object]]:
    records_by_surface = payload.get("candidate_records_by_surface_ref")
    if not isinstance(records_by_surface, dict):
        return []
    records: list[dict[str, object]] = []
    for values in records_by_surface.values():
        if isinstance(values, list):
            records.extend(record for record in values if isinstance(record, dict))
    return records


def _first_surface_and_node_ref(
    payload: dict[str, object],
) -> tuple[str | None, str | None]:
    surface_refs = payload.get("available_surface_refs")
    records_by_surface = payload.get("candidate_records_by_surface_ref")
    if not isinstance(surface_refs, list) or not isinstance(records_by_surface, dict):
        return None, None
    for surface_ref in surface_refs:
        if not isinstance(surface_ref, str):
            continue
        records = records_by_surface.get(surface_ref)
        if not isinstance(records, list):
            continue
        for record in records:
            if isinstance(record, dict) and isinstance(record.get("node_ref"), str):
                return surface_ref, record["node_ref"]
    return None, None


def _record_by_candidate_kind(
    records: list[dict[str, object]],
    candidate_kind: str,
) -> dict[str, object]:
    for record in records:
        if record.get("candidate_kind") == candidate_kind:
            return record
    raise AssertionError(f"candidate kind not found: {candidate_kind}")


def _record_by_node_ref_target(
    records: list[dict[str, object]],
    *,
    expected_candidate_kind: str,
) -> dict[str, object]:
    for record in records:
        if record.get("candidate_kind") == expected_candidate_kind:
            return record
    raise AssertionError(f"candidate kind not found near {SOURCE_KIND_ID}")
