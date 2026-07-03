from __future__ import annotations

import json

from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_one_step import run_r_loop_vessel_one_step

from tests.test_order_176_vessel_r_one_step_traversal import _record_packet


def test_r1_input_does_not_receive_candidate_text_or_samples() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()
    adapter = CapturingRLoopAdapter()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_177",
        user_question="source summary와 token layer summary 연결을 한 단계만 봐줘",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_177_blind_r1",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "completed"
    r1_payload = adapter.payloads_by_node["R1"]
    assert "entry_candidate_samples" not in r1_payload
    assert "summary_candidate_samples" not in r1_payload
    assert "summary_text" not in json.dumps(r1_payload, ensure_ascii=False)
    assert "summary_text_preview" not in json.dumps(r1_payload, ensure_ascii=False)
    assert "candidate_text_visibility_policy" in r1_payload


def test_r2_receives_core_entry_material_after_r1_blindness() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()
    adapter = CapturingRLoopAdapter()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_177",
        user_question="source summary와 token layer summary 연결을 한 단계만 봐줘",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_177_r2_r3_material",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "completed"
    r2_payload = adapter.payloads_by_node["R2"]
    r3_payload = adapter.payloads_by_node["R3"]
    assert "summary_candidate_records" not in r2_payload
    assert "candidate_layer_surface_ref_records" in r2_payload
    assert "candidate_records_by_surface_ref" in r2_payload
    assert "summary_text" not in json.dumps(r2_payload, ensure_ascii=False)
    selected = r3_payload["selected_candidate_record"]
    assert isinstance(selected, dict)
    assert selected["candidate_node_id"] == "graph:source_ingest_time_bundle:night_changed_sources"
    assert "summary_text" not in selected


def test_r1_goal_must_preserve_explicit_ascii_question_anchor() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_177",
        user_question="source summary token layer connection",
        read_packet=packet,
        adapter=DriftingR1Adapter(),
        frame_label="order_177_r1_anchor_fail",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "failed"
    assert result.result_frame.failure_stage == "R1"
    assert result.result_frame.failure_type == "schema_failed"
    assert "user_question_anchor_id" in (result.result_frame.failure_reason or "")


class CapturingRLoopAdapter:
    model_id = "capturing-r-loop-adapter"

    def __init__(self) -> None:
        self.payloads_by_node: dict[str, dict[str, object]] = {}

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            self.payloads_by_node["R1"] = request.input_payload
            payload = {
                "graph_search_goal": "Inspect source summary and token layer summary connection.",
                "user_question_anchor_id": request.input_payload["user_question_anchor"]["anchor_id"],
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 1,
                "stop_condition": "Stop after one selected candidate inspection.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            self.payloads_by_node["R2"] = request.input_payload
            available_surfaces = request.input_payload.get("available_surface_refs")
            records_by_surface = request.input_payload.get("candidate_records_by_surface_ref")
            selected_surface_id, selected_id = _first_summary_surface_and_node(
                available_surfaces,
                records_by_surface,
            )
            payload = {
                "selection_status": "selected",
                "selected_surface_ref": selected_surface_id,
                "selected_node_ref": selected_id,
                "selection_reason": "Select the first supplied candidate for visibility boundary test.",
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
                "inspection_reason": "The selected candidate material is sufficient for this one-step test.",
            }
        else:
            payload = {}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class DriftingR1Adapter:
    model_id = "drifting-r1-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "graph_search_goal": "Inspect ORDER 082 W1 triage output.",
            "user_question_anchor_id": "r1_user_question_anchor:wrong",
            "required_information_granularity": "low_summary",
            "allowed_summary_depth": 1,
            "stop_condition": "Stop after one selected candidate inspection.",
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def _first_summary_surface_and_node(
    available_surfaces: object,
    records_by_surface: object,
) -> tuple[str | None, str | None]:
    if not isinstance(available_surfaces, list) or not isinstance(records_by_surface, dict):
        return None, None
    fallback: tuple[str | None, str | None] = (None, None)
    for surface_id in available_surfaces:
        if not isinstance(surface_id, str):
            continue
        records = records_by_surface.get(surface_id)
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            node_ref = record.get("node_ref")
            if not isinstance(node_ref, str):
                continue
            if fallback == (None, None):
                fallback = (surface_id, node_ref)
            if record.get("summary_text"):
                return surface_id, node_ref
    return fallback
