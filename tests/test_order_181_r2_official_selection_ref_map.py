import json

from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_one_step import run_r_loop_vessel_one_step

from tests.test_order_178_r_vessel_candidate_layer_surface import (
    _record_multi_surface_packet,
)


def test_r2_uses_official_refs_and_code_maps_to_actual_graph_ids() -> None:
    trace_store, data_store, packet_event_id, packet = _record_multi_surface_packet()
    adapter = OfficialRefAdapter()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_181",
        user_question="공식 ref로 후보를 골라봐",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_181_ref_success",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "completed"
    assert result.r2_selection is not None
    assert result.r2_selection.selected_graph_node_id == (
        "graph:source_ingest_time_bundle:night_changed_sources"
    )
    r2_payload = adapter.payloads_by_node["R2"]
    assert r2_payload["available_surface_refs"][0] == "surface_001"
    grouped_json = json.dumps(
        r2_payload["candidate_records_by_surface_ref"],
        ensure_ascii=False,
    )
    assert "node_001" in grouped_json
    assert "graph:summary:source_leaf" not in grouped_json
    assert "graph:source_ingest_time_bundle:night_changed_sources" not in grouped_json


def test_r2_invented_short_refs_still_fail_with_diagnostics() -> None:
    trace_store, data_store, packet_event_id, packet = _record_multi_surface_packet()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_181",
        user_question="없는 ref를 만들면 실패해야 한다",
        read_packet=packet,
        adapter=InventedRefAdapter(),
        frame_label="order_181_invented_ref_fail",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "failed"
    assert result.result_frame.failure_stage == "R2"
    assert result.result_frame.failure_type == "schema_failed"
    summary = result.result_frame.failure_payload_summary
    assert summary is not None
    assert summary["selected_surface_ref"] == "surface_999"
    assert summary["selected_node_ref"] == "node_999"
    assert summary["selected_surface_ref_in_available"] is False
    assert summary["selected_node_ref_in_available"] is False


class OfficialRefAdapter:
    model_id = "official-ref-adapter"

    def __init__(self) -> None:
        self.payloads_by_node: dict[str, dict[str, object]] = {}

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            self.payloads_by_node["R1"] = request.input_payload
            payload = {
                "graph_search_goal": "Inspect official selection refs.",
                "user_question_anchor_id": request.input_payload["user_question_anchor"]["anchor_id"],
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 2,
                "stop_condition": "Stop after one selected candidate inspection.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            self.payloads_by_node["R2"] = request.input_payload
            surface_ref, candidate = _first_summary_candidate(request.input_payload)
            payload = {
                "selection_status": "selected",
                "selected_surface_ref": surface_ref,
                "selected_node_ref": candidate["node_ref"],
                "selection_reason": "Select the first official node ref in the first official surface.",
                "expected_information_granularity": "low_summary",
                "expected_source_kind": "summary",
            }
        elif "R3 Vessel Inspector" in request.prompt:
            self.payloads_by_node["R3"] = request.input_payload
            payload = {
                "current_information_granularity": "low_summary",
                "sufficiency_status": "sufficient",
                "granularity_problem_status": "none",
                "branch_problem_status": "none",
                "recommended_next_action": "stop",
                "inspection_reason": "Official ref was mapped to an actual graph node.",
            }
        else:
            payload = {}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def _first_summary_candidate(
    payload: dict[str, object],
) -> tuple[str, dict[str, object]]:
    available_surface_refs = payload["available_surface_refs"]
    records_by_surface = payload["candidate_records_by_surface_ref"]
    for surface_ref in available_surface_refs:
        records = records_by_surface[surface_ref]
        for record in records:
            if record.get("summary_text"):
                return surface_ref, record
    surface_ref = available_surface_refs[0]
    return surface_ref, records_by_surface[surface_ref][0]


class InventedRefAdapter(OfficialRefAdapter):
    model_id = "invented-ref-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R2 Vessel Node Selector" not in request.prompt:
            return super().complete(request)
        self.payloads_by_node["R2"] = request.input_payload
        payload = {
            "selection_status": "selected",
            "selected_surface_ref": "surface_999",
            "selected_node_ref": "node_999",
            "selection_reason": "Intentionally invent refs.",
            "expected_information_granularity": "low_summary",
            "expected_source_kind": "summary",
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )
