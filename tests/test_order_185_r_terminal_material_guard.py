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


def test_terminal_material_guard_rejects_axis_level_sufficient_stop() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet(
        entry_rows=[
            _time_axis_row(),
            _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
            _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
        ],
        summary_rows=[_summary_row()],
    )

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_185_guard",
        user_question="source summary와 token layer summary 연결을 계층적으로 탐색해",
        read_packet=packet,
        adapter=PrematureSufficientAdapter(),
        frame_label="order_185_guard",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.step_count == 4
    assert result.result_frame.selected_graph_node_ids == [
        "graph:axis:time",
        SOURCE_INGEST_ID,
        SOURCE_KIND_ID,
        SUMMARY_ID,
    ]
    assert result.result_frame.terminal_material_seen_count == 1
    assert result.result_frame.min_terminal_material_count == 1
    assert result.result_frame.early_stop_guard_trigger_count == 3
    assert result.result_frame.final_graph_node_id == SUMMARY_ID
    assert result.result_frame.final_continuation_status == "stop_sufficient"
    assert [
        continuation.continuation_reason_code
        for continuation in result.continuations[:3]
    ] == [
        "CODE_STATUS:r_loop_terminal_material_not_seen",
        "CODE_STATUS:r_loop_terminal_material_not_seen",
        "CODE_STATUS:r_loop_terminal_material_not_seen",
    ]
    assert result.continuations[-1].continuation_reason_code == "CODE_STATUS:r3_sufficient"


def _record_packet(
    *,
    entry_rows: list[dict[str, object]],
    summary_rows: list[dict[str, object]],
):
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_185_packet",
        batch_id="order_185_packet",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=entry_rows,
            summary_rows=summary_rows,
        ),
    )
    return trace_store, data_store, recorded.trace_event_id, recorded.packet


class PrematureSufficientAdapter:
    model_id = "premature-sufficient-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            payload = {
                "graph_search_goal": "Explore source summary and token layer summary connection.",
                "user_question_anchor_id": request.input_payload["user_question_anchor"]["anchor_id"],
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 1,
                "stop_condition": "Stop after enough terminal material is inspected.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            surface_ref, node_ref, candidate_kind = _first_visible_ref(request.input_payload)
            payload = {
                "selection_status": "selected",
                "selected_surface_ref": surface_ref,
                "selected_node_ref": node_ref,
                "selection_reason": "Select the first supplied candidate for guard testing.",
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
                "inspection_reason": "Prematurely claims the selected node is sufficient.",
            }
        else:
            payload = {}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def _first_visible_ref(payload: dict[str, object]) -> tuple[str | None, str | None, str | None]:
    surface_refs = payload.get("available_surface_refs")
    records_by_surface = payload.get("candidate_records_by_surface_ref")
    if not isinstance(surface_refs, list) or not isinstance(records_by_surface, dict):
        return None, None, None
    for surface_ref in surface_refs:
        if not isinstance(surface_ref, str):
            continue
        records = records_by_surface.get(surface_ref)
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            node_ref = record.get("node_ref")
            if isinstance(node_ref, str) and node_ref:
                candidate_kind = record.get("candidate_kind")
                return (
                    surface_ref,
                    node_ref,
                    candidate_kind if isinstance(candidate_kind, str) else None,
                )
    return None, None, None
