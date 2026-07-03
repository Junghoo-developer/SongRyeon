import json

from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_one_step import run_r_loop_vessel_one_step

from tests.test_order_178_r_vessel_candidate_layer_surface import (
    CapturingSurfaceAdapter,
    _record_multi_surface_packet,
)


def test_r2_candidate_payload_hides_non_selectable_graph_ids() -> None:
    trace_store, data_store, packet_event_id, packet = _record_multi_surface_packet()
    adapter = CapturingSurfaceAdapter()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_179",
        user_question="token layer summary 후보를 한 단계만 골라봐",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_179_payload_shape",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "completed"
    r2_payload = adapter.payloads_by_node["R2"]
    grouped_json = json.dumps(
        r2_payload["candidate_records_by_surface_ref"],
        ensure_ascii=False,
    )
    assert "node_ref" in grouped_json
    assert "summary_text" not in grouped_json
    assert "graph_node_id" not in grouped_json
    assert "target_graph_node_id" not in grouped_json
    assert "source_graph_node_ids" not in grouped_json
    assert "summary_node_id" not in grouped_json
    assert "candidate_node_id" not in grouped_json


def test_r2_invalid_target_style_id_reports_failure_payload_summary() -> None:
    trace_store, data_store, packet_event_id, packet = _record_multi_surface_packet()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_179",
        user_question="공식 node_ref가 아닌 값을 고르면 실패해야 한다",
        read_packet=packet,
        adapter=TargetStyleIdR2Adapter(),
        frame_label="order_179_target_id_fail",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "failed"
    assert result.result_frame.failure_stage == "R2"
    assert result.result_frame.failure_type == "schema_failed"
    summary = result.result_frame.failure_payload_summary
    assert summary is not None
    assert summary["selected_surface_ref_in_available"] is True
    assert summary["selected_node_ref"] == "node_missing"
    assert summary["selected_node_ref_in_available"] is False


class TargetStyleIdR2Adapter:
    model_id = "target-style-id-r2-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            payload = {
                "graph_search_goal": "Inspect node_ref selection boundary.",
                "user_question_anchor_id": request.input_payload["user_question_anchor"]["anchor_id"],
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 2,
                "stop_condition": "Stop after one selected candidate inspection.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            available_surfaces = request.input_payload.get("available_surface_refs")
            selected_surface_id = (
                available_surfaces[0]
                if isinstance(available_surfaces, list) and available_surfaces
                else None
            )
            payload = {
                "selection_status": "selected",
                "selected_surface_ref": selected_surface_id,
                "selected_node_ref": "node_missing",
                "selection_reason": "Intentionally choose a made-up node ref.",
                "expected_information_granularity": "low_summary",
                "expected_source_kind": "summary",
            }
        else:
            payload = {}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )
