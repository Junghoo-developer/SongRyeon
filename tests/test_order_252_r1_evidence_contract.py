from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import (
    record_r_loop_vessel_read_packet,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_one_step import (
    _record_satisfies_required_material_level,
    _updated_evidence_contract_material_ids,
    run_r_loop_vessel_one_step,
    run_r_loop_vessel_traverse,
)

from tests.test_order_175_vessel_backed_r_read_packet import READ_AT, _config
from tests.test_order_183_r_vessel_hierarchical_child_surface import (
    _source_ingest_row,
    _time_axis_row,
    _time_bundle_row,
)
from tests.test_order_184_r_vessel_multi_step_traversal import (
    SOURCE_KIND_ID,
    _source_kind_row,
)
from tests.test_order_187_r_vessel_summary_layer_before_raw import (
    LEAF_SUMMARY_ID,
    RAW_SOURCE_ID,
    TOKEN_SUMMARY_ID,
    _raw_source_row,
    _source_leaf_summary_row,
    _token_budget_summary_row,
)
from tests.test_order_234_r_rawsource_text_material_and_hierarchy_direction import (
    SOURCE_TEXT,
    SOURCE_TEXT_ID,
    _SourceTextDriverFactory,
    _source_text_row,
)


def test_new_r1_input_exposes_evidence_contract_without_legacy_minimum_fields() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet(
        include_raw_text=True
    )
    adapter = EvidenceContractAdapter(
        required_material_level="overview",
        required_material_count=1,
    )

    run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_252_input",
        user_question="상위 요약 하나를 확인해",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_252_input",
        input_ref=[packet_event_id],
    )

    assert adapter.r1_input_payload is not None
    contract = adapter.r1_input_payload["evidence_contract"]
    assert contract["output_fields"] == [
        "required_material_level",
        "required_material_count",
    ]
    assert "minimum_budget_contract" not in adapter.r1_input_payload


def test_raw_original_contract_forces_past_summaries_to_actual_text() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet(
        include_raw_text=True
    )
    adapter = EvidenceContractAdapter(
        required_material_level="raw_original",
        required_material_count=1,
    )

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_252_raw",
        user_question="ORDER 원문까지 확인해",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_252_raw",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.selected_graph_node_ids == [
        "graph:axis:time",
        "graph:source_ingest_time_bundle:night_changed_sources",
        SOURCE_KIND_ID,
        TOKEN_SUMMARY_ID,
        LEAF_SUMMARY_ID,
        RAW_SOURCE_ID,
    ]
    assert result.result_frame.raw_original_text_read_count == 1
    assert result.result_frame.required_material_level == "raw_original"
    assert result.result_frame.required_material_count == 1
    assert result.result_frame.evidence_contract_observed_count == 1
    assert result.result_frame.evidence_contract_status == "satisfied"
    assert result.result_frame.evidence_contract_material_node_ids == [RAW_SOURCE_ID]
    assert result.result_frame.r_loop_task_status == "sufficient"
    assert result.result_frame.early_stop_guard_trigger_count == 5
    assert all(
        continuation.continuation_reason_code
        == "CODE_STATUS:r_loop_evidence_contract_not_satisfied"
        for continuation in result.continuations[:5]
    )


def test_raw_source_without_text_closes_partial_instead_of_false_success() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet(
        include_raw_text=False
    )
    adapter = EvidenceContractAdapter(
        required_material_level="raw_original",
        required_material_count=1,
    )

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_252_missing_text",
        user_question="실제 원문까지 확인해",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_252_missing_text",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.final_graph_node_id == RAW_SOURCE_ID
    assert result.result_frame.raw_original_node_selected_count == 1
    assert result.result_frame.raw_original_text_read_count == 0
    assert result.result_frame.evidence_contract_observed_count == 0
    assert result.result_frame.evidence_contract_status == "unmet"
    assert result.result_frame.r_loop_task_status == "partial"
    assert result.result_frame.final_continuation_status == "stop_no_actionable_path"
    assert result.continuations[-1].continuation_reason_code == (
        "CODE_STATUS:r_loop_evidence_contract_unmet_no_actionable_path"
    )


def test_one_step_contract_unmet_is_partial_not_false_sufficient() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet(
        include_raw_text=True
    )
    adapter = EvidenceContractAdapter(
        required_material_level="raw_original",
        required_material_count=1,
    )

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_252_one_step",
        user_question="한 단계 정책에서도 원문 계약을 거짓 성공으로 닫지 마",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_252_one_step",
        input_ref=[packet_event_id],
    )

    assert result.return_summary is not None
    assert result.return_summary.r_loop_task_status == "partial"
    assert result.continuation is not None
    assert result.continuation.continuation_status == "stop_budget_exhausted"
    assert result.continuation.continuation_reason_code == (
        "CODE_STATUS:r_loop_evidence_contract_unmet_budget_exhausted"
    )


def test_source_summary_contract_and_unique_count_use_structural_fields() -> None:
    summary_record = {
        "summary_node_id": LEAF_SUMMARY_ID,
        "data_kind": "source_leaf_summary",
        "summary_text": "특정 원본 하나에 대응하는 요약",
    }
    assert _record_satisfies_required_material_level(
        summary_record,
        required_material_level="source_summary",
    )
    assert not _record_satisfies_required_material_level(
        summary_record,
        required_material_level="raw_original",
    )

    r1 = _legacy_free_r1_frame()
    once = _updated_evidence_contract_material_ids(
        r1=r1,
        selected_graph_node_id=LEAF_SUMMARY_ID,
        selected_record=summary_record,
        existing_node_ids=[],
    )
    twice = _updated_evidence_contract_material_ids(
        r1=r1,
        selected_graph_node_id=LEAF_SUMMARY_ID,
        selected_record=summary_record,
        existing_node_ids=once,
    )
    assert once == [LEAF_SUMMARY_ID]
    assert twice == [LEAF_SUMMARY_ID]


def _record_packet(*, include_raw_text: bool):
    raw_row = _raw_source_row(RAW_SOURCE_ID)
    raw_payload = json.loads(str(raw_row["payload_json"]))
    raw_payload["source_data_ids"] = [SOURCE_TEXT_ID]
    raw_row["payload_json"] = json.dumps(raw_payload, ensure_ascii=False)

    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_252_packet",
        batch_id="order_252_packet",
        config=_config(),
        created_at=READ_AT,
        driver_factory=_SourceTextDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
                _time_bundle_row(),
                _source_kind_row(source_graph_node_ids=[RAW_SOURCE_ID]),
                raw_row,
            ],
            summary_rows=[
                _source_leaf_summary_row(),
                _token_budget_summary_row(),
            ],
            source_text_rows=[_source_text_row()] if include_raw_text else [],
        ),
    )
    return trace_store, data_store, recorded.trace_event_id, recorded.packet


def _legacy_free_r1_frame():
    from songryeon_core.core.schemas import R1GraphGoalFrame

    return R1GraphGoalFrame(
        frame_id="R1:order_252:source_summary",
        graph_search_goal="개별 원본 요약을 확인한다.",
        required_information_granularity="low_summary",
        allowed_summary_depth=1,
        max_traversal_depth=6,
        max_branch_switches=0,
        max_node_reads=6,
        max_context_tokens=8000,
        stop_condition="Stop after the evidence contract is satisfied.",
        source_graph_guide_packet_id="r_loop:vessel_read_packet:order_252",
        required_material_level="source_summary",
        required_material_count=1,
        evidence_contract_mode="evidence_contract_v0",
        source_data_ids=["r_loop:vessel_read_packet:order_252"],
    )


class EvidenceContractAdapter:
    model_id = "order-252-evidence-contract-fake"

    def __init__(
        self,
        *,
        required_material_level: str,
        required_material_count: int,
    ) -> None:
        self.required_material_level = required_material_level
        self.required_material_count = required_material_count
        self.r1_input_payload: dict[str, object] | None = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            self.r1_input_payload = dict(request.input_payload)
            payload = {
                "graph_search_goal": "Inspect the requested Vessel evidence.",
                "user_question_anchor_id": request.input_payload[
                    "user_question_anchor"
                ]["anchor_id"],
                "required_material_level": self.required_material_level,
                "required_material_count": self.required_material_count,
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            surface_ref, node_ref, candidate_kind = _first_official_table_ref(
                request.input_payload
            )
            payload = {
                "selection_status": "selected" if node_ref else "none_selected",
                "selected_surface_ref": surface_ref if node_ref else None,
                "selected_node_ref": node_ref,
                "selection_reason": "Select the first official hierarchy candidate.",
                "expected_information_granularity": "raw",
                "expected_source_kind": candidate_kind or "candidate",
            }
        elif "R3 Vessel Inspector" in request.prompt:
            selected = request.input_payload.get("selected_candidate_record")
            raw_text_available = (
                isinstance(selected, dict)
                and selected.get("raw_original_text_status") == "available"
                and int(selected.get("raw_original_text_char_count") or 0) > 0
            )
            payload = {
                "current_information_granularity": (
                    "raw" if raw_text_available else "low_summary"
                ),
                "sufficiency_status": "sufficient",
                "granularity_problem_status": "none",
                "branch_problem_status": "none",
                "recommended_next_action": "stop",
                "inspection_reason": (
                    "The fake R3 always requests an early stop so code enforcement is tested."
                ),
            }
        else:
            payload = {}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def _first_official_table_ref(
    payload: dict[str, object],
) -> tuple[str | None, str | None, str | None]:
    table = payload.get("official_selection_table")
    if not isinstance(table, dict):
        return None, None, None
    rows = table.get("candidate_rows")
    if not isinstance(rows, list):
        return None, None, None
    for row in rows:
        if not isinstance(row, dict):
            continue
        surface_ref = row.get("surface_ref")
        node_ref = row.get("node_ref")
        candidate_kind = row.get("candidate_kind")
        if isinstance(surface_ref, str) and isinstance(node_ref, str):
            return (
                surface_ref,
                node_ref,
                candidate_kind if isinstance(candidate_kind, str) else None,
            )
    return None, None, None
