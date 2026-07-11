from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import record_r_loop_vessel_read_packet
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_one_step import (
    R_LOOP_VESSEL_ONE_STEP_GENERATOR,
    RLoopVesselOneStepFakeLLMAdapter,
    run_r_loop_vessel_one_step,
)
from songryeon_core.runtime.r_loop_vessel_one_step import (
    render_r_loop_vessel_one_step_text,
)

from tests.test_order_175_vessel_backed_r_read_packet import (
    READ_AT,
    FakeRLoopVesselDriverFactory,
    _config,
    _entry_rows,
    _summary_rows,
)


def test_vessel_r_one_step_runs_llm_r1_r2_r3_over_read_packet() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_176",
        user_question="송련 Core의 코드 요약 후보를 하나 골라봐",
        read_packet=packet,
        adapter=RLoopVesselOneStepFakeLLMAdapter(),
        frame_label="order_176_success",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "completed"
    assert result.r1_goal is not None
    assert result.candidate_layer_surface is not None
    assert result.surface_selection is not None
    assert result.r2_selection is not None
    assert result.r3_inspection is not None
    assert result.continuation is not None
    assert result.return_summary is not None
    assert result.r1_goal.generated_by.startswith("LLM:")
    assert result.r2_selection.generated_by.startswith("LLM:")
    assert result.r3_inspection.generated_by.startswith("LLM:")
    assert result.r2_selection.selected_graph_node_id in result.r2_selection.available_graph_node_ids
    assert result.r3_inspection.inspected_graph_node_id == result.r2_selection.selected_graph_node_id
    assert result.r3_inspection.sufficiency_status == "sufficient"
    assert result.continuation.continuation_status == "stop_sufficient"
    assert result.return_summary.r_loop_task_status == "sufficient"
    assert result.result_frame.generated_by == R_LOOP_VESSEL_ONE_STEP_GENERATOR
    assert result.result_frame.info_class == "absolute"
    assert result.result_frame.semantic_judgement_status == "not_run"


def test_vessel_r_one_step_rejects_r2_selection_outside_packet() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_176",
        user_question="지도 밖 후보를 고르면 실패해야 한다",
        read_packet=packet,
        adapter=BadR2SelectionAdapter(),
        frame_label="order_176_bad_r2",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "failed"
    assert result.result_frame.failure_stage == "R2"
    assert result.result_frame.failure_type == "schema_failed"
    assert "selected_node_ref" in (result.result_frame.failure_reason or "")
    assert result.result_frame.r1_goal_frame_id == "R1:order_176_bad_r2:vessel_goal_frame"
    assert result.result_frame.r2_selection_frame_id is None


def test_vessel_r_one_step_adapter_missing_does_not_select_candidate() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_176",
        user_question="adapter가 없으면 선택하지 마라",
        read_packet=packet,
        adapter=None,
        frame_label="order_176_adapter_missing",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "failed"
    assert result.result_frame.failure_stage == "adapter"
    assert result.result_frame.failure_type == "adapter_missing"
    assert result.result_frame.selected_graph_node_id is None
    assert result.result_frame.llm_call_data_ids == []


def test_vessel_r3_child_ids_are_copied_from_packet_not_llm() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_176",
        user_question="R3가 없는 child id를 만들지 못해야 한다",
        read_packet=packet,
        adapter=InventingR3Adapter(),
        frame_label="order_176_r3_child_guard",
        input_ref=[packet_event_id],
    )

    assert result.r3_inspection is not None
    assert result.r3_inspection.child_node_ids == []
    assert "graph:invented:child" not in result.r3_inspection.child_node_ids
    assert result.r3_inspection.recommended_next_action == "stop"
    assert result.continuation is not None
    assert result.continuation.continuation_status == "stop_sufficient"


def test_vessel_r_one_step_records_expected_frames_in_datastore() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_176",
        user_question="기록되는 frame들을 확인해",
        read_packet=packet,
        adapter=RLoopVesselOneStepFakeLLMAdapter(),
        frame_label="order_176_records",
        input_ref=[packet_event_id],
    )

    data_types = {
        data_store.require_record(data_id).data_type
        for data_id in result.output_data_ids
    }
    assert "node_output:R1_graph_goal_frame" in data_types
    assert "r_loop:vessel_candidate_layer_surface" in data_types
    assert "node_output:R_loop_vessel_surface_selection_frame" in data_types
    assert "node_output:R2_graph_node_selection_frame" in data_types
    assert "node_output:R3_graph_inspection_frame" in data_types
    assert "node_output:R_loop_continuation_frame" in data_types
    assert "node_output:R_loop_return_summary_frame" in data_types
    assert "r_loop:vessel_one_step_result" in data_types


def test_vessel_r_one_step_text_renderer_prints_llm_reasons() -> None:
    rendered = render_r_loop_vessel_one_step_text(
        {
            "status": "R_LOOP_VESSEL_ONE_STEP_OK",
            "one_step_status": "completed",
            "read_packet_status": "passed",
            "entry_candidate_count": 2,
            "summary_candidate_count": 1,
            "selected_graph_node_id": "graph:summary:source_leaf:code_tools",
            "inspected_graph_node_id": "graph:summary:source_leaf:code_tools",
            "sufficiency_status": "sufficient",
            "continuation_status": "stop_sufficient",
            "r_loop_task_status": "sufficient",
            "r1_goal_frame": {
                "graph_search_goal": "Inspect one active Vessel summary candidate.",
                "required_information_granularity": "low_summary",
            },
            "r2_selection_frame": {
                "selection_reason": "Selected the active code summary.",
            },
            "r3_inspection_frame": {
                "inspection_reason": "The summary is sufficient for one step.",
            },
        }
    )

    assert "one_step_status: completed" in rendered
    assert "selected_graph_node_id: graph:summary:source_leaf:code_tools" in rendered
    assert "R1 goal: Inspect one active Vessel summary candidate." in rendered
    assert "R2 selection_reason: Selected the active code summary." in rendered
    assert "R3 inspection_reason: The summary is sufficient for one step." in rendered


def _record_packet():
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_176",
        batch_id="order_176_packet",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows(),
            summary_rows=_summary_rows(),
        ),
    )
    return trace_store, data_store, recorded.trace_event_id, recorded.packet


class BadR2SelectionAdapter:
    model_id = "bad-r2-selection-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            payload = {
                "graph_search_goal": "Test invalid R2 selection.",
                "user_question_anchor_id": request.input_payload["user_question_anchor"]["anchor_id"],
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 1,
                "stop_condition": "Stop after one selected candidate inspection.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            available_surfaces = request.input_payload.get("available_surface_refs")
            surface_id = (
                available_surfaces[0]
                if isinstance(available_surfaces, list) and available_surfaces
                else None
            )
            payload = {
                "selection_status": "selected",
                "selected_surface_ref": surface_id,
                "selected_node_ref": "node_missing",
                "selection_reason": "This intentionally violates the allowed ID list.",
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


class InventingR3Adapter:
    model_id = "inventing-r3-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            payload = {
                "graph_search_goal": "Test R3 child id boundary.",
                "user_question_anchor_id": request.input_payload["user_question_anchor"]["anchor_id"],
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 1,
                "stop_condition": "Stop after one selected candidate inspection.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
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
                "selection_reason": "Select the first supplied candidate.",
                "expected_information_granularity": "low_summary",
                "expected_source_kind": "summary",
            }
        elif "R3 Vessel Inspector" in request.prompt:
            payload = {
                "current_information_granularity": "low_summary",
                "sufficiency_status": "sufficient",
                "granularity_problem_status": "none",
                "branch_problem_status": "none",
                "recommended_next_action": "stop",
                "inspection_reason": "Return a valid decision while attempting to attach a fabricated child field.",
                "child_node_ids": ["graph:invented:child"],
            }
        else:
            payload = {}
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
