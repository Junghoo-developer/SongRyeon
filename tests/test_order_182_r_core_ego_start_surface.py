import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import record_r_loop_vessel_read_packet
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_one_step import run_r_loop_vessel_one_step

from tests.test_order_175_vessel_backed_r_read_packet import (
    READ_AT,
    FakeRLoopVesselDriverFactory,
    _config,
    _entry_rows,
    _summary_rows,
)


def test_r2_first_view_hides_summary_candidates_even_when_packet_has_them() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet(_entry_rows())
    adapter = CapturingCoreStartAdapter()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_182",
        user_question="CoreEgo에서 한 단계만 내려가 봐",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_182_core_start",
        input_ref=[packet_event_id],
    )

    assert packet.summary_candidate_count == 1
    assert result.result_frame.one_step_status == "completed"
    assert result.candidate_layer_surface is not None
    assert all(
        record["surface_kind"] == "entry_candidate_kind"
        for record in result.candidate_layer_surface.surface_records
    )

    r2_payload = adapter.payloads_by_node["R2"]
    grouped_json = json.dumps(
        r2_payload["candidate_records_by_surface_ref"],
        ensure_ascii=False,
    )
    assert "summary_text" not in grouped_json
    assert "summary_node_id" not in grouped_json
    assert "source_leaf_summary" not in grouped_json
    assert r2_payload["selection_ref_contract"]["current_graph_node_id"] == "graph:core_ego:root"
    assert (
        r2_payload["selection_ref_contract"]["first_step_policy"]
        == "core_ego_direct_entry_candidates_only"
    )


def test_time_axis_entry_is_prioritized_as_core_ego_direct_child() -> None:
    entry_rows = [_time_axis_row(), *_entry_rows()]
    trace_store, data_store, packet_event_id, packet = _record_packet(entry_rows)
    adapter = CapturingCoreStartAdapter()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_182_axis",
        user_question="CoreEgo 바로 아래 시간축을 먼저 봐",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_182_time_axis",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "completed"
    assert result.r2_selection is not None
    assert result.r2_selection.selected_graph_node_id == "graph:axis:time"
    assert result.candidate_layer_surface is not None
    assert result.candidate_layer_surface.surface_count == 1
    surface = result.candidate_layer_surface.surface_records[0]
    assert surface["candidate_kind"] == "time_axis"
    assert surface["candidate_graph_node_ids"] == ["graph:axis:time"]


def _record_packet(entry_rows: list[dict[str, object]]):
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_182_packet",
        batch_id="order_182_packet",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=entry_rows,
            summary_rows=_summary_rows(),
        ),
    )
    return trace_store, data_store, recorded.trace_event_id, recorded.packet


def _time_axis_row() -> dict[str, object]:
    return {
        "candidate_node_id": "graph:axis:time",
        "display_name": "Time Axis",
        "node_kind": "time_axis",
        "data_kind": "time_axis",
        "created_at": "2026-07-02T00:00:00",
        "written_at": "2026-07-02T00:00:00",
        "source_trace_id": None,
        "payload_json": json.dumps(
            {
                "node_kind": "time_axis",
                "data_kind": "time_axis",
                "summary_depth": 0,
                "source_leaf_count": 0,
                "source_summary_count": 0,
            },
            ensure_ascii=False,
        ),
        "labels": ["GraphMemoryNode", "TimeAxis"],
    }


class CapturingCoreStartAdapter:
    model_id = "capturing-core-start-adapter"

    def __init__(self) -> None:
        self.payloads_by_node: dict[str, dict[str, object]] = {}

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            self.payloads_by_node["R1"] = request.input_payload
            payload = {
                "graph_search_goal": "Inspect the direct CoreEgo entry layer.",
                "user_question_anchor_id": request.input_payload["user_question_anchor"]["anchor_id"],
                "required_information_granularity": "raw",
                "allowed_summary_depth": 0,
                "stop_condition": "Stop after one entry candidate inspection.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            self.payloads_by_node["R2"] = request.input_payload
            surface_ref, node_ref = _first_visible_node_ref(request.input_payload)
            payload = {
                "selection_status": "selected",
                "selected_surface_ref": surface_ref,
                "selected_node_ref": node_ref,
                "selection_reason": "Select the first direct CoreEgo entry candidate.",
                "expected_information_granularity": "raw",
                "expected_source_kind": "entry_candidate",
            }
        elif "R3 Vessel Inspector" in request.prompt:
            self.payloads_by_node["R3"] = request.input_payload
            payload = {
                "current_information_granularity": "raw",
                "sufficiency_status": "sufficient",
                "granularity_problem_status": "none",
                "branch_problem_status": "none",
                "recommended_next_action": "stop",
                "inspection_reason": "The selected CoreEgo entry candidate is visible.",
            }
        else:
            payload = {}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def _first_visible_node_ref(payload: dict[str, object]) -> tuple[str | None, str | None]:
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
            if not isinstance(record, dict):
                continue
            node_ref = record.get("node_ref")
            if isinstance(node_ref, str) and node_ref:
                return surface_ref, node_ref
    return None, None
