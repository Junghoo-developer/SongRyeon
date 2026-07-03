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
    _time_bundle_row,
)


def test_time_axis_child_surface_exposes_structural_branch_roles() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()
    adapter = BranchRoleCaptureAdapter()

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_191_branch_roles",
        user_question="source summary와 token summary 구조를 확인해줘",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_191_branch_roles",
        input_ref=[packet_event_id],
        max_node_reads=2,
        max_traversal_depth=2,
    )

    assert result.result_frame.traverse_status == "completed"
    assert len(result.candidate_layer_surfaces) == 2

    child_surface = result.candidate_layer_surfaces[1]
    branch_roles = [
        record["branch_role"] for record in child_surface.surface_records
    ]
    assert branch_roles == [
        "source_material_ingest",
        "conversation_time_memory",
    ]
    assert child_surface.surface_records[0]["candidate_kind"] == "source_ingest_bundle"
    assert child_surface.surface_records[1]["candidate_kind"] == "time_bundle"

    second_r2_payload = adapter.r2_payloads[1]
    surface_records = second_r2_payload["candidate_layer_surface_ref_records"]
    assert surface_records[0]["branch_role"] == "source_material_ingest"
    assert surface_records[1]["branch_role"] == "conversation_time_memory"

    records_by_surface = second_r2_payload["candidate_records_by_surface_ref"]
    source_surface_ref = surface_records[0]["surface_ref"]
    time_surface_ref = surface_records[1]["surface_ref"]
    assert records_by_surface[source_surface_ref][0]["branch_role"] == (
        "source_material_ingest"
    )
    assert records_by_surface[time_surface_ref][0]["branch_role"] == (
        "conversation_time_memory"
    )


def test_structural_surface_order_keeps_source_ingest_before_time_bundle() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_191_source_first",
        user_question="source summary와 token summary 구조를 확인해줘",
        read_packet=packet,
        adapter=BranchRoleCaptureAdapter(),
        frame_label="order_191_source_first",
        input_ref=[packet_event_id],
        max_node_reads=2,
        max_traversal_depth=2,
    )

    assert result.result_frame.selected_graph_node_ids[:2] == [
        "graph:axis:time",
        "graph:source_ingest_time_bundle:night_changed_sources",
    ]
    assert "graph:time_bundle:manual_vessel_first_write:core" not in (
        result.result_frame.selected_graph_node_ids
    )


class BranchRoleCaptureAdapter:
    model_id = "order-191-branch-role-capture-fake"

    def __init__(self) -> None:
        self.r2_payloads: list[dict[str, object]] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            payload = {
                "graph_search_goal": "Inspect source summary and token summary graph branches",
                "user_question_anchor_id": request.input_payload["user_question_anchor"]["anchor_id"],
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 1,
                "stop_condition": "Stop after the structural branch entry is inspected.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            self.r2_payloads.append(request.input_payload)
            surface_ref, node_ref = _first_ref(request.input_payload)
            payload = {
                "selection_status": "selected" if node_ref else "none_selected",
                "selected_surface_ref": surface_ref if node_ref else None,
                "selected_node_ref": node_ref,
                "selection_reason": "Select the first structurally ordered official candidate.",
                "expected_information_granularity": "low_summary",
                "expected_source_kind": "structural_branch_candidate",
            }
        elif "R3 Vessel Inspector" in request.prompt:
            child_count = request.input_payload.get("hierarchy_child_candidate_count")
            has_children = isinstance(child_count, int) and child_count > 0
            payload = {
                "current_information_granularity": "low_summary",
                "sufficiency_status": "insufficient" if has_children else "unknown",
                "granularity_problem_status": (
                    "needs_lower_granularity" if has_children else "unknown"
                ),
                "branch_problem_status": "none",
                "recommended_next_action": "deeper" if has_children else "fail",
                "inspection_reason": (
                    "Child branch candidates are available."
                    if has_children
                    else "No child branch candidates are available."
                ),
            }
        else:
            payload = {"error": "unknown prompt"}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def _first_ref(payload: dict[str, object]) -> tuple[str | None, str | None]:
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


def _record_packet():
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_191_packet",
        batch_id="order_191_packet",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(),
                _time_bundle_row(),
            ],
            summary_rows=[],
        ),
    )
    return trace_store, data_store, recorded.trace_event_id, recorded.packet
