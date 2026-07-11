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
    SOURCE_KIND_ID,
    SUMMARY_ID,
    _source_kind_row,
    _summary_row,
)


def test_r2_second_step_receives_continuation_work_order() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()
    adapter = ContinuationWorkOrderCaptureAdapter()

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_228_capture",
        user_question="R3가 deeper를 내면 다음 R2 작업지시서를 확인해",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_228_capture",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert len(adapter.r2_payloads) >= 2
    second_payload = adapter.r2_payloads[1]
    work_order = second_payload["continuation_work_order"]

    assert work_order["work_order_status"] == "continuation"
    assert work_order["previous_r3_recommended_next_action"] == "deeper"
    assert work_order["previous_continuation_status"] == "continue_deeper"
    assert work_order["candidate_count"] > 0
    assert work_order["none_selected_allowed"] is False
    assert second_payload["official_selection_table"]["candidate_rows"]


def test_r2_none_selected_is_repaired_when_work_order_requires_selection() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()
    adapter = NoneSelectedThenRepairAdapter()

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_228_repair",
        user_question="작업지시서가 있으면 R2 none_selected를 수리해",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_228_repair",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.selected_graph_node_ids[:2] == [
        "graph:axis:time",
        "graph:source_ingest_time_bundle:night_changed_sources",
    ]
    assert adapter.saw_forbidden_work_order is True
    assert adapter.repair_selected_surface_ref is not None
    assert adapter.repair_selected_node_ref is not None

    r2_calls = [
        record.payload
        for record in data_store.list_records()
        if record.data_type == "llm_call"
        and isinstance(record.payload, dict)
        and record.payload.get("node_id") == "R2_vessel_node_selector"
    ]
    assert any(call["failure_type"] == "schema_failed" for call in r2_calls)


def _record_packet():
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_228_packet",
        batch_id="order_228_packet",
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


class ContinuationWorkOrderCaptureAdapter:
    model_id = "order-228-continuation-work-order-fake"

    def __init__(self) -> None:
        self.r2_payloads: list[dict[str, object]] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            payload = {
                "graph_search_goal": "Inspect deeper child candidates after R3 requests deeper.",
                "user_question_anchor_id": request.input_payload["user_question_anchor"]["anchor_id"],
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 1,
                "min_traversal_depth": 0,
                "min_node_reads": 0,
                "min_terminal_material_count": 0,
                "stop_condition": "Stop after the second inspected node is enough.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            self.r2_payloads.append(dict(request.input_payload))
            surface_ref, node_ref, candidate_kind = _first_official_table_ref(
                request.input_payload
            )
            payload = {
                "selection_status": "selected" if node_ref else "none_selected",
                "selected_surface_ref": surface_ref if node_ref else None,
                "selected_node_ref": node_ref,
                "selection_reason": "Select the first official candidate.",
                "expected_information_granularity": "low_summary",
                "expected_source_kind": candidate_kind or "candidate",
            }
        elif "R3 Vessel Inspector" in request.prompt:
            selected = request.input_payload.get("selected_candidate_record")
            candidate_kind = selected.get("candidate_kind") if isinstance(selected, dict) else None
            go_deeper = candidate_kind == "time_axis"
            payload = {
                "current_information_granularity": "low_summary",
                "sufficiency_status": "insufficient" if go_deeper else "sufficient",
                "granularity_problem_status": (
                    "needs_lower_granularity" if go_deeper else "none"
                ),
                "branch_problem_status": "none",
                "recommended_next_action": "deeper" if go_deeper else "stop",
                "inspection_reason": (
                    "Time axis needs child candidate inspection."
                    if go_deeper
                    else "Second selected node is enough for this test."
                ),
            }
        else:
            payload = {}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class NoneSelectedThenRepairAdapter(ContinuationWorkOrderCaptureAdapter):
    model_id = "order-228-none-selected-repair-fake"

    def __init__(self) -> None:
        super().__init__()
        self.returned_bad_none_selected = False
        self.saw_forbidden_work_order = False
        self.repair_selected_surface_ref: str | None = None
        self.repair_selected_node_ref: str | None = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R2 Vessel Node Selector" not in request.prompt:
            return super().complete(request)

        self.r2_payloads.append(dict(request.input_payload))
        work_order = request.input_payload.get("continuation_work_order")
        forbidden = (
            isinstance(work_order, dict)
            and work_order.get("none_selected_allowed") is False
        )
        if forbidden and "schema_repair_request" not in request.input_payload:
            self.saw_forbidden_work_order = True
            self.returned_bad_none_selected = True
            payload = {
                "selection_status": "none_selected",
                "selected_surface_ref": None,
                "selected_node_ref": None,
                "selection_reason": "Intentional bad none_selected despite continuation work order.",
                "expected_information_granularity": "low_summary",
                "expected_source_kind": "none",
            }
        else:
            source_payload = request.input_payload
            if "schema_repair_request" in request.input_payload:
                source_payload = request.input_payload["r2_copy_repair_table"]
            surface_ref, node_ref, candidate_kind = _first_official_table_ref(
                source_payload
            )
            self.repair_selected_surface_ref = surface_ref
            self.repair_selected_node_ref = node_ref
            payload = {
                "selection_status": "selected" if node_ref else "none_selected",
                "selected_surface_ref": surface_ref if node_ref else None,
                "selected_node_ref": node_ref,
                "selection_reason": "Repair selected one official candidate required by work order.",
                "expected_information_granularity": "low_summary",
                "expected_source_kind": candidate_kind or "candidate",
            }
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
