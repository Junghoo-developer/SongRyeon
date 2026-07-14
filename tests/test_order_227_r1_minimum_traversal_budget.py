from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import record_r_loop_vessel_read_packet
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_one_step import run_r_loop_vessel_traverse

from tests.test_order_175_vessel_backed_r_read_packet import (
    READ_AT,
    FakeRLoopVesselDriverFactory,
    _config,
)
from tests.test_order_183_r_vessel_hierarchical_child_surface import (
    _source_ingest_row,
    _time_axis_row,
)
from tests.test_order_184_r_vessel_multi_step_traversal import (
    SOURCE_INGEST_ID,
    SOURCE_KIND_ID,
    SUMMARY_ID,
    _source_kind_row,
    _summary_row,
)


def test_r1_payload_contains_hierarchy_primer_and_evidence_contract() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()
    adapter = R1MinimumBudgetAdapter(min_node_reads=1)

    run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_227_payload",
        user_question="R1 최소 예산 입력 구조를 확인해",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_227_payload",
        input_ref=[packet_event_id],
    )

    assert adapter.r1_payload is not None
    assert adapter.r1_payload["hierarchy_primer"]["visibility"] == (
        "structure_only_without_candidate_ids_or_content"
    )
    assert adapter.r1_payload["evidence_contract"]["output_fields"] == [
        "required_material_level",
        "required_material_count",
    ]
    assert "minimum_budget_contract" not in adapter.r1_payload


def test_r1_minimum_node_reads_prevents_premature_r3_stop() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()
    adapter = R1MinimumBudgetAdapter(min_node_reads=3)

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_227_minimum",
        user_question="R3가 너무 빨리 충분하다고 해도 R1 최소 노드 읽기 수를 지켜",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_227_minimum",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.r1_goal is not None
    assert result.r1_goal.evidence_contract_mode == (
        "legacy_minimum_budget_compatibility"
    )
    assert result.r1_goal.min_node_reads == 3
    assert result.final_budget is not None
    assert result.final_budget.min_node_reads == 3
    assert result.result_frame.step_count == 3
    assert result.result_frame.selected_graph_node_ids == [
        "graph:axis:time",
        SOURCE_INGEST_ID,
        SOURCE_KIND_ID,
    ]
    assert result.result_frame.final_continuation_status == "stop_sufficient"
    assert result.result_frame.early_stop_guard_trigger_count == 2
    assert [
        continuation.continuation_reason_code
        for continuation in result.continuations[:2]
    ] == [
        "CODE_STATUS:r_loop_r1_minimum_budget_not_satisfied",
        "CODE_STATUS:r_loop_r1_minimum_budget_not_satisfied",
    ]


def _record_packet():
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_227_packet",
        batch_id="order_227_packet",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
                _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
            ],
            summary_rows=[_summary_row()],
        ),
    )
    return trace_store, data_store, recorded.trace_event_id, recorded.packet


class R1MinimumBudgetAdapter:
    model_id = "order-227-r1-minimum-budget-fake"

    def __init__(self, *, min_node_reads: int) -> None:
        self.min_node_reads = min_node_reads
        self.r1_payload: dict[str, object] | None = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            self.r1_payload = dict(request.input_payload)
            payload = {
                "graph_search_goal": "Traverse enough graph layers before accepting sufficiency.",
                "user_question_anchor_id": request.input_payload["user_question_anchor"]["anchor_id"],
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 1,
                "min_traversal_depth": 0,
                "min_node_reads": self.min_node_reads,
                "min_terminal_material_count": 0,
                "stop_condition": "Stop only after the minimum R1 node-read budget is satisfied.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            surface_ref, node_ref, candidate_kind = _first_official_table_ref(
                request.input_payload
            )
            payload = {
                "selection_status": "selected" if node_ref else "none_selected",
                "selected_surface_ref": surface_ref if node_ref else None,
                "selected_node_ref": node_ref,
                "selection_reason": "Select the first official candidate for minimum-budget testing.",
                "expected_information_granularity": "low_summary",
                "expected_source_kind": candidate_kind or "candidate",
            }
        elif "R3 Vessel Inspector" in request.prompt:
            payload = {
                "current_information_granularity": "low_summary",
                "sufficiency_status": "sufficient",
                "granularity_problem_status": "none",
                "branch_problem_status": "none",
                "recommended_next_action": "stop",
                "inspection_reason": "Prematurely claims the current node is sufficient.",
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
