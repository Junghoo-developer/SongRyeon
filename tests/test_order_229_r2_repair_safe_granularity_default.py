from __future__ import annotations

import json

from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_one_step import run_r_loop_vessel_traverse

from tests.test_order_228_r_continuation_work_order import (
    _first_official_table_ref,
    _record_packet,
)


def test_r2_repair_uses_safe_granularity_default() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()
    adapter = BadGranularityThenSafeRepairAdapter()

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_229_safe_granularity",
        user_question="R2 수리 모드에서 정보 농도 enum 안전 기본값을 확인해",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_229_safe_granularity",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.selected_graph_node_ids == ["graph:axis:time"]
    assert adapter.repair_default_granularity == "unknown"

    r2_frames = [
        record.payload
        for record in data_store.list_records()
        if record.data_type == "node_output:R2_graph_node_selection_frame"
        and isinstance(record.payload, dict)
    ]
    assert r2_frames[0]["expected_information_granularity"] == "unknown"

    r2_calls = [
        record.payload
        for record in data_store.list_records()
        if record.data_type == "llm_call"
        and isinstance(record.payload, dict)
        and record.payload.get("node_id") == "R2_vessel_node_selector"
    ]
    assert [call["failure_type"] for call in r2_calls] == ["schema_failed", "none"]


class BadGranularityThenSafeRepairAdapter:
    model_id = "order-229-r2-safe-granularity-fake"

    def __init__(self) -> None:
        self.repair_default_granularity: str | None = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            payload = {
                "graph_search_goal": "Inspect one entry node and stop.",
                "user_question_anchor_id": request.input_payload["user_question_anchor"][
                    "anchor_id"
                ],
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 1,
                "min_traversal_depth": 0,
                "min_node_reads": 0,
                "min_terminal_material_count": 0,
                "stop_condition": "Stop after the first inspected node.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            source_payload = request.input_payload
            if "schema_repair_request" in request.input_payload:
                source_payload = request.input_payload["r2_copy_repair_table"]
                defaults = source_payload["safe_output_defaults"]
                self.repair_default_granularity = defaults["expected_information_granularity"]
                granularity = self.repair_default_granularity
            else:
                granularity = "child_candidate"
            surface_ref, node_ref, candidate_kind = _first_official_table_ref(source_payload)
            payload = {
                "selection_status": "selected",
                "selected_surface_ref": surface_ref,
                "selected_node_ref": node_ref,
                "selection_reason": "Select the first official candidate.",
                "expected_information_granularity": granularity,
                "expected_source_kind": candidate_kind or "candidate",
            }
        elif "R3 Vessel Inspector" in request.prompt:
            payload = {
                "current_information_granularity": "low_summary",
                "sufficiency_status": "sufficient",
                "granularity_problem_status": "none",
                "branch_problem_status": "none",
                "recommended_next_action": "stop",
                "inspection_reason": "First inspected node is enough for this test.",
            }
        else:
            payload = {}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )
