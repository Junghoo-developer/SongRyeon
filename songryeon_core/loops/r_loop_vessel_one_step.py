from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_state_machine import decide_r_loop_continuation
from songryeon_core.core.r_loop_vessel_read_packet import RLoopVesselReadPacketFrame
from songryeon_core.core.schemas import (
    R1GraphGoalFrame,
    R2GraphNodeSelectionFrame,
    R3GraphInspectionFrame,
    RGraphTraversalCandidateSurfaceFrame,
    RLoopBudgetFrame,
    RLoopContinuationFrame,
    RLoopReturnSummaryFrame,
    validate_r1_graph_goal_frame,
    validate_r2_graph_node_selection_frame,
    validate_r3_graph_inspection_frame,
    validate_r_graph_traversal_candidate_surface_frame,
    validate_r_loop_budget_frame,
    validate_r_loop_continuation_frame,
    validate_r_loop_return_summary_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter, LLMRequest, LLMResponse
from songryeon_core.llm.node_executor import LLMNodeExecutor


R_LOOP_VESSEL_ONE_STEP_GENERATOR = "CODE:R_LOOP_VESSEL_ONE_STEP_ASSEMBLER"
R_LOOP_VESSEL_ONE_STEP_RESULT_DATA_TYPE = "r_loop:vessel_one_step_result"
R_LOOP_VESSEL_ONE_STEP_SCHEMA_NAME = "RLoopVesselOneStepResultFrame"
R_LOOP_VESSEL_ONE_STEP_POLICY_ID = "R_LOOP_VESSEL_ONE_STEP_TRAVERSAL_V0"
R_LOOP_VESSEL_ONE_STEP_STATUSES = {"completed", "failed", "not_run"}
R_LOOP_VESSEL_TRAVERSE_GENERATOR = "CODE:R_LOOP_VESSEL_MULTI_STEP_ASSEMBLER"
R_LOOP_VESSEL_TRAVERSE_RESULT_DATA_TYPE = "r_loop:vessel_traverse_result"
R_LOOP_VESSEL_TRAVERSE_SCHEMA_NAME = "RLoopVesselTraverseResultFrame"
R_LOOP_VESSEL_TRAVERSE_POLICY_ID = "R_LOOP_VESSEL_MULTI_STEP_TRAVERSAL_MVP_V0"
R_LOOP_VESSEL_TRAVERSE_STATUSES = {"completed", "failed", "not_run"}
R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_GENERATOR = (
    "CODE:R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_BUILDER"
)
R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_DATA_TYPE = (
    "r_loop:vessel_candidate_layer_surface"
)
R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_SCHEMA_NAME = (
    "RLoopVesselCandidateLayerSurfaceFrame"
)
R_LOOP_VESSEL_SURFACE_SELECTION_DATA_TYPE = (
    "node_output:R_loop_vessel_surface_selection_frame"
)
R_LOOP_VESSEL_SURFACE_SELECTION_SCHEMA_NAME = "RLoopVesselSurfaceSelectionFrame"

R1_VESSEL_GOAL_PROMPT_REF = "songryeon_core/prompts/r1_vessel_goal_setter_v0.md"
R2_VESSEL_SELECTOR_PROMPT_REF = "songryeon_core/prompts/r2_vessel_node_selector_v0.md"
R3_VESSEL_INSPECTOR_PROMPT_REF = "songryeon_core/prompts/r3_vessel_inspector_v0.md"

R1_VESSEL_NODE_ID = "R1_vessel_goal_setter"
R2_VESSEL_NODE_ID = "R2_vessel_node_selector"
R3_VESSEL_NODE_ID = "R3_vessel_inspector"

R_ONE_STEP_MAX_TRAVERSAL_DEPTH = 1
R_ONE_STEP_MAX_BRANCH_SWITCHES = 0
R_ONE_STEP_MAX_NODE_READS = 1
R_ONE_STEP_MAX_CONTEXT_TOKENS = 4000
R_TRAVERSE_MAX_TRAVERSAL_DEPTH = 6
R_TRAVERSE_MAX_BRANCH_SWITCHES = 0
R_TRAVERSE_MAX_NODE_READS = 6
R_TRAVERSE_MAX_CONTEXT_TOKENS = 8000
R_TRAVERSE_MIN_TERMINAL_MATERIAL_READS = 1
R_TRAVERSE_MAX_RAW_ORIGINAL_MATERIAL_READS = 5


@dataclass(frozen=True)
class RLoopVesselOneStepResultFrame:
    frame_id: str
    created_at: str
    policy_id: str
    one_step_status: str
    failure_stage: str | None
    failure_type: str | None
    failure_reason: str | None
    source_packet_id: str
    r1_goal_frame_id: str | None
    r2_selection_frame_id: str | None
    r3_inspection_frame_id: str | None
    budget_frame_id: str | None
    continuation_frame_id: str | None
    return_summary_frame_id: str | None
    selected_graph_node_id: str | None
    inspected_graph_node_id: str | None
    sufficiency_status: str | None
    continuation_status: str | None
    llm_call_data_ids: list[str]
    output_data_ids: list[str]
    source_data_ids: list[str]
    source_trace_ids: list[str]
    failure_payload_summary: dict[str, object] | None = None
    generated_by: str = R_LOOP_VESSEL_ONE_STEP_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R_LOOP_VESSEL_ONE_STEP_SCHEMA_NAME


@dataclass(frozen=True)
class RLoopVesselTraverseResultFrame:
    frame_id: str
    created_at: str
    policy_id: str
    traverse_status: str
    failure_stage: str | None
    failure_type: str | None
    failure_reason: str | None
    source_packet_id: str
    r1_goal_frame_id: str | None
    final_budget_frame_id: str | None
    return_summary_frame_id: str | None
    step_count: int
    selected_graph_node_ids: list[str]
    inspected_graph_node_ids: list[str]
    candidate_surface_frame_ids: list[str]
    graph_traversal_candidate_surface_frame_ids: list[str]
    r2_selection_frame_ids: list[str]
    r3_inspection_frame_ids: list[str]
    continuation_frame_ids: list[str]
    final_graph_node_id: str | None
    final_sufficiency_status: str | None
    final_continuation_status: str | None
    r_loop_task_status: str | None
    final_information_granularity: str | None
    summary_depth_used: int | None
    terminal_material_seen_count: int
    min_terminal_material_count: int
    raw_original_material_seen_count: int
    max_raw_original_material_count: int
    raw_original_read_cap_reached: bool
    early_stop_guard_trigger_count: int
    llm_call_data_ids: list[str]
    output_data_ids: list[str]
    source_data_ids: list[str]
    source_trace_ids: list[str]
    failure_payload_summary: dict[str, object] | None = None
    generated_by: str = R_LOOP_VESSEL_TRAVERSE_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R_LOOP_VESSEL_TRAVERSE_SCHEMA_NAME


@dataclass(frozen=True)
class RLoopVesselCandidateLayerSurfaceFrame:
    frame_id: str
    created_at: str
    source_packet_id: str
    surface_count: int
    total_candidate_count: int
    available_surface_ids: list[str]
    surface_records: list[dict[str, object]]
    source_data_ids: list[str]
    source_trace_ids: list[str]
    generated_by: str = R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_SCHEMA_NAME


@dataclass(frozen=True)
class RLoopVesselSurfaceSelectionFrame:
    frame_id: str
    selection_scope: str
    available_surface_ids: list[str]
    selection_status: str
    selected_surface_id: str | None
    selected_surface_candidate_count: int
    surface_selection_reason: str
    source_r1_goal_frame_id: str
    source_surface_frame_id: str
    source_data_ids: list[str]
    source_trace_ids: list[str]
    generated_by: str
    info_class: str = "mixed"
    semantic_judgement_status: str = "ran"
    schema_name: str = R_LOOP_VESSEL_SURFACE_SELECTION_SCHEMA_NAME


@dataclass(frozen=True)
class RLoopVesselOneStepRun:
    result_frame: RLoopVesselOneStepResultFrame
    r1_goal: R1GraphGoalFrame | None
    budget: RLoopBudgetFrame | None
    r2_selection: R2GraphNodeSelectionFrame | None
    r3_inspection: R3GraphInspectionFrame | None
    continuation: RLoopContinuationFrame | None
    return_summary: RLoopReturnSummaryFrame | None
    trace_event_ids: list[str]
    output_data_ids: list[str]
    candidate_layer_surface: RLoopVesselCandidateLayerSurfaceFrame | None = None
    surface_selection: RLoopVesselSurfaceSelectionFrame | None = None
    graph_traversal_candidate_surface: RGraphTraversalCandidateSurfaceFrame | None = None


@dataclass(frozen=True)
class RLoopVesselTraverseRun:
    result_frame: RLoopVesselTraverseResultFrame
    r1_goal: R1GraphGoalFrame | None
    final_budget: RLoopBudgetFrame | None
    r2_selections: list[R2GraphNodeSelectionFrame]
    r3_inspections: list[R3GraphInspectionFrame]
    continuations: list[RLoopContinuationFrame]
    return_summary: RLoopReturnSummaryFrame | None
    candidate_layer_surfaces: list[RLoopVesselCandidateLayerSurfaceFrame]
    surface_selections: list[RLoopVesselSurfaceSelectionFrame]
    graph_traversal_candidate_surfaces: list[RGraphTraversalCandidateSurfaceFrame]
    trace_event_ids: list[str]
    output_data_ids: list[str]


class RLoopVesselOneStepFakeLLMAdapter:
    """Deterministic fake adapter for the R Vessel one-step CLI/tests."""

    model_id = "r-loop-vessel-one-step-fake-llm-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            user_question = str(request.input_payload.get("user_question") or "").strip()
            payload = {
                "graph_search_goal": (
                    "Inspect one active Vessel summary candidate for the current question"
                    f": {user_question}"
                ),
                "user_question_anchor_id": _r1_anchor_id_from_input_payload(
                    request.input_payload
                ),
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 1,
                "stop_condition": "Stop after one selected candidate inspection.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            available_surfaces = request.input_payload.get("available_surface_refs")
            selected_surface_id = None
            records_by_surface = request.input_payload.get("candidate_records_by_surface_ref")
            selected_id = None
            if isinstance(available_surfaces, list) and isinstance(records_by_surface, dict):
                for surface_id in available_surfaces:
                    if not isinstance(surface_id, str) or not surface_id:
                        continue
                    value = records_by_surface.get(surface_id)
                    if not isinstance(value, list):
                        continue
                    for item in value:
                        if (
                            isinstance(item, dict)
                            and isinstance(item.get("node_ref"), str)
                            and item.get("node_ref")
                            and item.get("summary_text")
                        ):
                            selected_surface_id = surface_id
                            selected_id = str(item["node_ref"])
                            break
                    if selected_id:
                        break
                if not selected_id:
                    selected_surface_id = next(
                        (item for item in available_surfaces if isinstance(item, str) and item),
                        None,
                    )
                    if selected_surface_id:
                        value = records_by_surface.get(selected_surface_id)
                        if isinstance(value, list):
                            selected_id = next(
                                (
                                    str(item.get("node_ref"))
                                    for item in value
                                    if isinstance(item, dict)
                                    and isinstance(item.get("node_ref"), str)
                                    and item.get("node_ref")
                                ),
                                None,
                            )
            payload = {
                "selection_status": "selected" if selected_id else "none_selected",
                "selected_surface_ref": selected_surface_id if selected_id else None,
                "selected_node_ref": selected_id,
                "selection_reason": (
                    "Fake adapter selected the first supplied candidate inside the first supplied Vessel surface."
                    if selected_id
                    else "Fake adapter received no available Vessel candidates."
                ),
                "expected_information_granularity": "low_summary",
                "expected_source_kind": "summary_or_entry_candidate",
            }
        elif "R3 Vessel Inspector" in request.prompt:
            selected = request.input_payload.get("selected_candidate_record")
            summary_text = ""
            selected_node_id = ""
            if isinstance(selected, dict):
                summary_text = str(selected.get("summary_text") or "")
                selected_node_id = str(
                    selected.get("summary_node_id")
                    or selected.get("candidate_node_id")
                    or ""
                )
            has_candidate_material = bool(summary_text or selected_node_id)
            payload = {
                "current_information_granularity": (
                    "low_summary" if summary_text else "raw" if selected_node_id else "unknown"
                ),
                "sufficiency_status": "sufficient" if has_candidate_material else "insufficient",
                "granularity_problem_status": "none" if has_candidate_material else "needs_lower_granularity",
                "branch_problem_status": "none",
                "recommended_next_action": "stop" if has_candidate_material else "deeper",
                "inspection_reason": (
                    "Fake adapter treats supplied summary text as sufficient for one-step smoke."
                    if summary_text
                    else "Fake adapter treats the supplied entry candidate as sufficient for one-step smoke."
                    if selected_node_id
                    else "Fake adapter found no selected candidate material."
                ),
            }
        else:
            payload = {"error": "unknown R Vessel one-step prompt"}
        import json

        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class RLoopVesselTraverseFakeLLMAdapter:
    """Deterministic fake adapter for multi-step R Vessel traversal tests/CLI."""

    model_id = "r-loop-vessel-traverse-fake-llm-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            user_question = str(request.input_payload.get("user_question") or "").strip()
            payload = {
                "graph_search_goal": f"Traverse Vessel hierarchy for: {user_question}",
                "user_question_anchor_id": _r1_anchor_id_from_input_payload(
                    request.input_payload
                ),
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 1,
                "stop_condition": "Stop when a selected summary is sufficient or traversal budget ends.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            surface_ref, node_ref, expected_source_kind = _first_visible_ref(
                request.input_payload,
            )
            payload = {
                "selection_status": "selected" if node_ref else "none_selected",
                "selected_surface_ref": surface_ref if node_ref else None,
                "selected_node_ref": node_ref,
                "selection_reason": (
                    "Fake traversal adapter selected the first visible hierarchy candidate."
                    if node_ref
                    else "Fake traversal adapter received no hierarchy candidates."
                ),
                "expected_information_granularity": "low_summary",
                "expected_source_kind": expected_source_kind or "hierarchy_candidate",
            }
        elif "R3 Vessel Inspector" in request.prompt:
            selected = request.input_payload.get("selected_candidate_record")
            summary_text = ""
            if isinstance(selected, dict):
                summary_text = str(selected.get("summary_text") or "")
            child_count = request.input_payload.get("hierarchy_child_candidate_count")
            has_children = isinstance(child_count, int) and child_count > 0
            sufficient = bool(summary_text) or not has_children
            payload = {
                "current_information_granularity": "low_summary" if summary_text else "raw",
                "sufficiency_status": "sufficient" if sufficient else "insufficient",
                "granularity_problem_status": "none" if sufficient else "needs_lower_granularity",
                "branch_problem_status": "none",
                "recommended_next_action": "stop" if sufficient else "deeper",
                "inspection_reason": (
                    "Fake traversal adapter treats selected summary text as sufficient."
                    if summary_text
                    else "Fake traversal adapter recommends deeper traversal because child candidates exist."
                    if has_children
                    else "Fake traversal adapter stops because no child candidates remain."
                ),
            }
        else:
            payload = {"error": "unknown R Vessel traversal prompt"}
        import json

        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def run_r_loop_vessel_one_step(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    user_question: str,
    read_packet: RLoopVesselReadPacketFrame,
    adapter: LLMAdapter | None,
    frame_label: str = "manual_vessel_r_one_step",
    input_ref: list[str] | None = None,
) -> RLoopVesselOneStepRun:
    frame_label = _safe_frame_label(frame_label)
    source_trace_ids = _unique_strings([*(input_ref or []), *read_packet.source_trace_ids])
    result_frame_id = _result_frame_id(frame_label)
    if read_packet.read_status != "passed":
        return _record_failure_result(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame_id=result_frame_id,
            created_at=_now_from_trace(trace_store),
            source_packet_id=read_packet.packet_id,
            failure_stage="read_packet",
            failure_type=read_packet.failure_type or "read_packet_not_passed",
            failure_reason=read_packet.failure_reason or "R Vessel read packet is not passed.",
            source_data_ids=[read_packet.packet_id],
            source_trace_ids=source_trace_ids,
        )
    if adapter is None:
        return _record_failure_result(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame_id=result_frame_id,
            created_at=_now_from_trace(trace_store),
            source_packet_id=read_packet.packet_id,
            failure_stage="adapter",
            failure_type="adapter_missing",
            failure_reason="R Vessel one-step traversal requires an LLM adapter.",
            source_data_ids=[read_packet.packet_id],
            source_trace_ids=source_trace_ids,
        )

    executor = LLMNodeExecutor(adapter)
    llm_call_data_ids: list[str] = []
    trace_event_ids: list[str] = []
    output_data_ids: list[str] = []

    r1_result = executor.run(
        node_id=R1_VESSEL_NODE_ID,
        prompt=_prompt(R1_VESSEL_GOAL_PROMPT_REF),
        input_payload=_r1_input_payload(
            user_question=user_question,
            read_packet=read_packet,
            policy_name="one_step",
            max_traversal_depth=R_ONE_STEP_MAX_TRAVERSAL_DEPTH,
            max_branch_switches=R_ONE_STEP_MAX_BRANCH_SWITCHES,
            max_node_reads=R_ONE_STEP_MAX_NODE_READS,
            max_context_tokens=R_ONE_STEP_MAX_CONTEXT_TOKENS,
        ),
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=R1_VESSEL_GOAL_PROMPT_REF,
        input_ref=source_trace_ids,
        source_data_ids=[read_packet.packet_id],
        payload_validator=lambda payload: _validate_r1_payload(
            payload,
            read_packet=read_packet,
            user_question=user_question,
        ),
    )
    _append_llm_refs(r1_result, llm_call_data_ids, trace_event_ids)
    if r1_result.failure_type != "none" or r1_result.validation.payload is None:
        return _record_failure_result(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame_id=result_frame_id,
            created_at=_now_from_trace(trace_store),
            source_packet_id=read_packet.packet_id,
            failure_stage="R1",
            failure_type=r1_result.failure_type,
            failure_reason=r1_result.validation.error or "R1 payload validation failed.",
            source_data_ids=_unique_strings([read_packet.packet_id, r1_result.call_data_id]),
            source_trace_ids=_unique_strings([*source_trace_ids, r1_result.trace_event_id]),
            llm_call_data_ids=llm_call_data_ids,
        )

    r1 = _r1_frame_from_payload(
        payload=r1_result.validation.payload,
        frame_label=frame_label,
        read_packet=read_packet,
        model_id=r1_result.model_id,
        llm_call_data_id=r1_result.call_data_id,
        source_trace_ids=_unique_strings([*source_trace_ids, r1_result.trace_event_id]),
    )
    _record_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        actor="R1",
        data_type="node_output:R1_graph_goal_frame",
        frame_id=r1.frame_id,
        payload=asdict(r1),
        input_ref=_unique_strings([*source_trace_ids, r1_result.trace_event_id]),
        trace_event_ids=trace_event_ids,
        output_data_ids=output_data_ids,
    )

    budget = _budget_frame(r1=r1, frame_label=frame_label)
    _record_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        actor="R:budget",
        data_type="node_output:R_loop_budget_frame",
        frame_id=budget.frame_id,
        payload=asdict(budget),
        input_ref=[r1.frame_id],
        trace_event_ids=trace_event_ids,
        output_data_ids=output_data_ids,
    )

    candidate_layer_surface = _candidate_layer_surface_frame(
        frame_label=frame_label,
        read_packet=read_packet,
        created_at=_now_from_trace(trace_store),
    )
    _record_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        actor="R:candidate_layer_surface",
        data_type=R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_DATA_TYPE,
        frame_id=candidate_layer_surface.frame_id,
        payload=asdict(candidate_layer_surface),
        input_ref=[read_packet.packet_id],
        trace_event_ids=trace_event_ids,
        output_data_ids=output_data_ids,
    )

    available_graph_node_ids = _available_graph_node_ids(read_packet)
    r2_result = executor.run(
        node_id=R2_VESSEL_NODE_ID,
        prompt=_prompt(R2_VESSEL_SELECTOR_PROMPT_REF),
        input_payload=_r2_input_payload(
            user_question=user_question,
            read_packet=read_packet,
            r1=r1,
            candidate_layer_surface=candidate_layer_surface,
            available_graph_node_ids=available_graph_node_ids,
        ),
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=R2_VESSEL_SELECTOR_PROMPT_REF,
        input_ref=_unique_strings([*source_trace_ids, *trace_event_ids]),
        source_data_ids=[read_packet.packet_id, r1.frame_id, candidate_layer_surface.frame_id],
        payload_validator=lambda payload: _validate_r2_payload(
            payload,
            available_graph_node_ids=available_graph_node_ids,
            candidate_layer_surface=candidate_layer_surface,
        ),
    )
    _append_llm_refs(r2_result, llm_call_data_ids, trace_event_ids)
    if r2_result.failure_type != "none" or r2_result.validation.payload is None:
        return _record_failure_result(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame_id=result_frame_id,
            created_at=_now_from_trace(trace_store),
            source_packet_id=read_packet.packet_id,
            failure_stage="R2",
            failure_type=r2_result.failure_type,
            failure_reason=r2_result.validation.error or "R2 payload validation failed.",
            source_data_ids=_unique_strings(
                [
                    read_packet.packet_id,
                    r1.frame_id,
                    candidate_layer_surface.frame_id,
                    r2_result.call_data_id,
                ]
            ),
            source_trace_ids=_unique_strings([*source_trace_ids, *trace_event_ids, r2_result.trace_event_id]),
            llm_call_data_ids=llm_call_data_ids,
            r1_goal_frame_id=r1.frame_id,
            budget_frame_id=budget.frame_id,
            output_data_ids=output_data_ids,
            failure_payload_summary=_r2_failure_payload_summary(
                r2_result.validation.payload,
                available_graph_node_ids=available_graph_node_ids,
                candidate_layer_surface=candidate_layer_surface,
            ),
        )

    surface_selection = _surface_selection_frame_from_payload(
        payload=r2_result.validation.payload,
        frame_label=frame_label,
        r1=r1,
        candidate_layer_surface=candidate_layer_surface,
        model_id=r2_result.model_id,
        llm_call_data_id=r2_result.call_data_id,
        source_trace_ids=_unique_strings([*source_trace_ids, r2_result.trace_event_id]),
    )
    _record_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        actor="R2:surface",
        data_type=R_LOOP_VESSEL_SURFACE_SELECTION_DATA_TYPE,
        frame_id=surface_selection.frame_id,
        payload=asdict(surface_selection),
        input_ref=_unique_strings([*source_trace_ids, r2_result.trace_event_id]),
        trace_event_ids=trace_event_ids,
        output_data_ids=output_data_ids,
    )

    r2 = _r2_frame_from_payload(
        payload=r2_result.validation.payload,
        frame_label=frame_label,
        read_packet=read_packet,
        r1=r1,
        candidate_layer_surface=candidate_layer_surface,
        available_graph_node_ids=_surface_candidate_ids_for_selection(
            candidate_layer_surface,
            surface_selection.selected_surface_id,
            fallback_graph_node_ids=available_graph_node_ids,
        ),
        model_id=r2_result.model_id,
        llm_call_data_id=r2_result.call_data_id,
        source_trace_ids=_unique_strings([*source_trace_ids, r2_result.trace_event_id]),
    )
    _record_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        actor="R2",
        data_type="node_output:R2_graph_node_selection_frame",
        frame_id=r2.frame_id,
        payload=asdict(r2),
        input_ref=_unique_strings([*source_trace_ids, r2_result.trace_event_id]),
        trace_event_ids=trace_event_ids,
        output_data_ids=output_data_ids,
    )

    if r2.selection_status != "selected" or r2.selected_graph_node_id is None:
        return_summary = _return_summary_for_no_selection(
            frame_label=frame_label,
            read_packet=read_packet,
            r1=r1,
            budget=budget,
            r2=r2,
        )
        _record_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            actor="R:return_summary",
            data_type="node_output:R_loop_return_summary_frame",
            frame_id=return_summary.frame_id,
            payload=asdict(return_summary),
            input_ref=[r2.frame_id],
            trace_event_ids=trace_event_ids,
            output_data_ids=output_data_ids,
        )
        result_frame = _result_frame(
            frame_id=result_frame_id,
            created_at=_now_from_trace(trace_store),
            one_step_status="completed",
            source_packet_id=read_packet.packet_id,
            r1_goal_frame_id=r1.frame_id,
            r2_selection_frame_id=r2.frame_id,
            budget_frame_id=budget.frame_id,
            return_summary_frame_id=return_summary.frame_id,
            llm_call_data_ids=llm_call_data_ids,
            output_data_ids=output_data_ids,
            source_data_ids=[read_packet.packet_id, r1.frame_id, budget.frame_id, r2.frame_id, return_summary.frame_id],
            source_trace_ids=_unique_strings([*source_trace_ids, *trace_event_ids]),
        )
        _record_result_frame(trace_store, data_store, turn_id, result_frame, trace_event_ids, output_data_ids)
        return RLoopVesselOneStepRun(
            result_frame=result_frame,
            r1_goal=r1,
            budget=budget,
            r2_selection=r2,
            r3_inspection=None,
            continuation=None,
            return_summary=return_summary,
            trace_event_ids=trace_event_ids,
            output_data_ids=output_data_ids,
            candidate_layer_surface=candidate_layer_surface,
            surface_selection=surface_selection,
        )

    selected_record = _selected_candidate_record(read_packet, r2.selected_graph_node_id)
    r3_result = executor.run(
        node_id=R3_VESSEL_NODE_ID,
        prompt=_prompt(R3_VESSEL_INSPECTOR_PROMPT_REF),
        input_payload=_r3_input_payload(
            user_question=user_question,
            r1=r1,
            r2=r2,
            selected_record=selected_record,
        ),
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=R3_VESSEL_INSPECTOR_PROMPT_REF,
        input_ref=_unique_strings([*source_trace_ids, *trace_event_ids]),
        source_data_ids=[read_packet.packet_id, r1.frame_id, r2.frame_id, r2.selected_graph_node_id],
        payload_validator=_validate_r3_payload,
    )
    _append_llm_refs(r3_result, llm_call_data_ids, trace_event_ids)
    if r3_result.failure_type != "none" or r3_result.validation.payload is None:
        return _record_failure_result(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame_id=result_frame_id,
            created_at=_now_from_trace(trace_store),
            source_packet_id=read_packet.packet_id,
            failure_stage="R3",
            failure_type=r3_result.failure_type,
            failure_reason=r3_result.validation.error or "R3 payload validation failed.",
            source_data_ids=_unique_strings(
                [
                    read_packet.packet_id,
                    r1.frame_id,
                    budget.frame_id,
                    candidate_layer_surface.frame_id,
                    surface_selection.frame_id,
                    r2.frame_id,
                    r3_result.call_data_id,
                ]
            ),
            source_trace_ids=_unique_strings([*source_trace_ids, *trace_event_ids, r3_result.trace_event_id]),
            llm_call_data_ids=llm_call_data_ids,
            r1_goal_frame_id=r1.frame_id,
            r2_selection_frame_id=r2.frame_id,
            budget_frame_id=budget.frame_id,
            selected_graph_node_id=r2.selected_graph_node_id,
            output_data_ids=output_data_ids,
        )

    r3 = _r3_frame_from_payload(
        payload=r3_result.validation.payload,
        frame_label=frame_label,
        selected_record=selected_record,
        read_packet=read_packet,
        r2=r2,
        model_id=r3_result.model_id,
        llm_call_data_id=r3_result.call_data_id,
        source_trace_ids=_unique_strings([*source_trace_ids, r3_result.trace_event_id]),
    )
    _record_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        actor="R3",
        data_type="node_output:R3_graph_inspection_frame",
        frame_id=r3.frame_id,
        payload=asdict(r3),
        input_ref=_unique_strings([*source_trace_ids, r3_result.trace_event_id]),
        trace_event_ids=trace_event_ids,
        output_data_ids=output_data_ids,
    )

    graph_traversal_candidate_surface = _graph_traversal_candidate_surface_frame(
        frame_label=frame_label,
        r3=r3,
        selected_record=selected_record,
    )
    _record_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        actor="R:graph_traversal_candidate_surface",
        data_type="node_output:R_graph_traversal_candidate_surface_frame",
        frame_id=graph_traversal_candidate_surface.frame_id,
        payload=asdict(graph_traversal_candidate_surface),
        input_ref=[r3.frame_id],
        trace_event_ids=trace_event_ids,
        output_data_ids=output_data_ids,
    )

    continuation = decide_r_loop_continuation(
        frame_id=f"R:{frame_label}:vessel_one_step_continuation_frame",
        r3_inspection=r3,
        budget=budget,
        source_trace_ids=_unique_strings([*source_trace_ids, *trace_event_ids]),
    )
    validate_r_loop_continuation_frame(continuation)
    _record_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        actor="R:continuation",
        data_type="node_output:R_loop_continuation_frame",
        frame_id=continuation.frame_id,
        payload=asdict(continuation),
        input_ref=[r3.frame_id, budget.frame_id],
        trace_event_ids=trace_event_ids,
        output_data_ids=output_data_ids,
    )

    return_summary = _return_summary_for_completed_step(
        frame_label=frame_label,
        read_packet=read_packet,
        r1=r1,
        budget=budget,
        r2=r2,
        r3=r3,
        continuation=continuation,
    )
    _record_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        actor="R:return_summary",
        data_type="node_output:R_loop_return_summary_frame",
        frame_id=return_summary.frame_id,
        payload=asdict(return_summary),
        input_ref=[continuation.frame_id],
        trace_event_ids=trace_event_ids,
        output_data_ids=output_data_ids,
    )

    result_frame = _result_frame(
        frame_id=result_frame_id,
        created_at=_now_from_trace(trace_store),
        one_step_status="completed",
        source_packet_id=read_packet.packet_id,
        r1_goal_frame_id=r1.frame_id,
        r2_selection_frame_id=r2.frame_id,
        r3_inspection_frame_id=r3.frame_id,
        budget_frame_id=budget.frame_id,
        continuation_frame_id=continuation.frame_id,
        return_summary_frame_id=return_summary.frame_id,
        selected_graph_node_id=r2.selected_graph_node_id,
        inspected_graph_node_id=r3.inspected_graph_node_id,
        sufficiency_status=r3.sufficiency_status,
        continuation_status=continuation.continuation_status,
        llm_call_data_ids=llm_call_data_ids,
        output_data_ids=output_data_ids,
        source_data_ids=[
            read_packet.packet_id,
            r1.frame_id,
            budget.frame_id,
            candidate_layer_surface.frame_id,
            surface_selection.frame_id,
            r2.frame_id,
            r3.frame_id,
            graph_traversal_candidate_surface.frame_id,
            continuation.frame_id,
            return_summary.frame_id,
            r2.selected_graph_node_id,
        ],
        source_trace_ids=_unique_strings([*source_trace_ids, *trace_event_ids]),
    )
    _record_result_frame(trace_store, data_store, turn_id, result_frame, trace_event_ids, output_data_ids)
    return RLoopVesselOneStepRun(
        result_frame=result_frame,
        r1_goal=r1,
        budget=budget,
        r2_selection=r2,
        r3_inspection=r3,
        continuation=continuation,
        return_summary=return_summary,
        trace_event_ids=trace_event_ids,
        output_data_ids=output_data_ids,
        candidate_layer_surface=candidate_layer_surface,
        surface_selection=surface_selection,
        graph_traversal_candidate_surface=graph_traversal_candidate_surface,
    )


def run_r_loop_vessel_traverse(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    user_question: str,
    read_packet: RLoopVesselReadPacketFrame,
    adapter: LLMAdapter | None,
    frame_label: str = "manual_vessel_r_traverse",
    input_ref: list[str] | None = None,
    max_traversal_depth: int = R_TRAVERSE_MAX_TRAVERSAL_DEPTH,
    max_node_reads: int = R_TRAVERSE_MAX_NODE_READS,
    max_branch_switches: int = R_TRAVERSE_MAX_BRANCH_SWITCHES,
    max_context_tokens: int = R_TRAVERSE_MAX_CONTEXT_TOKENS,
    max_raw_original_material_reads: int = R_TRAVERSE_MAX_RAW_ORIGINAL_MATERIAL_READS,
    start_handoff_packet_id: str | None = None,
) -> RLoopVesselTraverseRun:
    frame_label = _safe_frame_label(frame_label)
    source_trace_ids = _unique_strings([*(input_ref or []), *read_packet.source_trace_ids])
    base_source_data_ids = _unique_strings([read_packet.packet_id, start_handoff_packet_id])
    result_frame_id = _traverse_result_frame_id(frame_label)
    if read_packet.read_status != "passed":
        return _record_traverse_failure_result(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame_id=result_frame_id,
            created_at=_now_from_trace(trace_store),
            source_packet_id=read_packet.packet_id,
            failure_stage="read_packet",
            failure_type=read_packet.failure_type or "read_packet_not_passed",
            failure_reason=read_packet.failure_reason or "R Vessel read packet is not passed.",
            source_data_ids=base_source_data_ids,
            source_trace_ids=source_trace_ids,
        )
    if adapter is None:
        return _record_traverse_failure_result(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame_id=result_frame_id,
            created_at=_now_from_trace(trace_store),
            source_packet_id=read_packet.packet_id,
            failure_stage="adapter",
            failure_type="adapter_missing",
            failure_reason="R Vessel traversal requires an LLM adapter.",
            source_data_ids=base_source_data_ids,
            source_trace_ids=source_trace_ids,
        )

    executor = LLMNodeExecutor(adapter)
    llm_call_data_ids: list[str] = []
    trace_event_ids: list[str] = []
    output_data_ids: list[str] = []
    candidate_layer_surfaces: list[RLoopVesselCandidateLayerSurfaceFrame] = []
    surface_selections: list[RLoopVesselSurfaceSelectionFrame] = []
    r2_selections: list[R2GraphNodeSelectionFrame] = []
    r3_inspections: list[R3GraphInspectionFrame] = []
    graph_surfaces: list[RGraphTraversalCandidateSurfaceFrame] = []
    continuations: list[RLoopContinuationFrame] = []
    terminal_material_seen_count = 0
    raw_original_material_seen_count = 0
    raw_original_read_cap_reached = False
    early_stop_guard_trigger_count = 0

    r1_result = executor.run(
        node_id=R1_VESSEL_NODE_ID,
        prompt=_prompt(R1_VESSEL_GOAL_PROMPT_REF),
        input_payload=_r1_input_payload(
            user_question=user_question,
            read_packet=read_packet,
            policy_name="multi_step_traversal",
            max_traversal_depth=max_traversal_depth,
            max_branch_switches=max_branch_switches,
            max_node_reads=max_node_reads,
            max_context_tokens=max_context_tokens,
        ),
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=R1_VESSEL_GOAL_PROMPT_REF,
        input_ref=source_trace_ids,
        source_data_ids=base_source_data_ids,
        payload_validator=lambda payload: _validate_r1_payload(
            payload,
            read_packet=read_packet,
            user_question=user_question,
        ),
    )
    _append_llm_refs(r1_result, llm_call_data_ids, trace_event_ids)
    if r1_result.failure_type != "none" or r1_result.validation.payload is None:
        return _record_traverse_failure_result(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame_id=result_frame_id,
            created_at=_now_from_trace(trace_store),
            source_packet_id=read_packet.packet_id,
            failure_stage="R1",
            failure_type=r1_result.failure_type,
            failure_reason=r1_result.validation.error or "R1 payload validation failed.",
            source_data_ids=_unique_strings([*base_source_data_ids, r1_result.call_data_id]),
            source_trace_ids=_unique_strings([*source_trace_ids, r1_result.trace_event_id]),
            llm_call_data_ids=llm_call_data_ids,
        )

    r1 = _r1_frame_from_payload(
        payload=r1_result.validation.payload,
        frame_label=frame_label,
        read_packet=read_packet,
        model_id=r1_result.model_id,
        llm_call_data_id=r1_result.call_data_id,
        source_trace_ids=_unique_strings([*source_trace_ids, r1_result.trace_event_id]),
        max_traversal_depth=max_traversal_depth,
        max_branch_switches=max_branch_switches,
        max_node_reads=max_node_reads,
        max_context_tokens=max_context_tokens,
    )
    _record_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        actor="R1",
        data_type="node_output:R1_graph_goal_frame",
        frame_id=r1.frame_id,
        payload=asdict(r1),
        input_ref=_unique_strings([*source_trace_ids, r1_result.trace_event_id]),
        trace_event_ids=trace_event_ids,
        output_data_ids=output_data_ids,
    )

    next_candidate_surface = _candidate_layer_surface_frame(
        frame_label=f"{frame_label}_step_0001",
        read_packet=read_packet,
        created_at=_now_from_trace(trace_store),
    )
    final_budget: RLoopBudgetFrame | None = None
    final_continuation: RLoopContinuationFrame | None = None
    return_summary: RLoopReturnSummaryFrame | None = None

    for step_index in range(1, max_node_reads + 1):
        step_label = f"{frame_label}_step_{step_index:04d}"
        candidate_layer_surface = next_candidate_surface
        candidate_layer_surfaces.append(candidate_layer_surface)
        _record_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            actor="R:candidate_layer_surface",
            data_type=R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_DATA_TYPE,
            frame_id=candidate_layer_surface.frame_id,
            payload=asdict(candidate_layer_surface),
            input_ref=[read_packet.packet_id],
            trace_event_ids=trace_event_ids,
            output_data_ids=output_data_ids,
        )

        available_graph_node_ids = _surface_all_candidate_ids(candidate_layer_surface)
        r2_result = executor.run(
            node_id=R2_VESSEL_NODE_ID,
            prompt=_prompt(R2_VESSEL_SELECTOR_PROMPT_REF),
            input_payload=_r2_input_payload(
                user_question=user_question,
                read_packet=read_packet,
                r1=r1,
                candidate_layer_surface=candidate_layer_surface,
                available_graph_node_ids=available_graph_node_ids,
                current_graph_node_id=_surface_current_graph_node_id(candidate_layer_surface),
                traversal_policy="hierarchical_child_candidates"
                if step_index > 1
                else "core_ego_direct_entry_candidates_only",
            ),
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            prompt_ref=R2_VESSEL_SELECTOR_PROMPT_REF,
            input_ref=_unique_strings([*source_trace_ids, *trace_event_ids]),
            source_data_ids=[
                *base_source_data_ids,
                r1.frame_id,
                candidate_layer_surface.frame_id,
            ],
            payload_validator=lambda payload, surface=candidate_layer_surface, ids=available_graph_node_ids: _validate_r2_payload(
                payload,
                available_graph_node_ids=ids,
                candidate_layer_surface=surface,
            ),
        )
        _append_llm_refs(r2_result, llm_call_data_ids, trace_event_ids)
        if r2_result.failure_type != "none" or r2_result.validation.payload is None:
            return _record_traverse_failure_result(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                frame_id=result_frame_id,
                created_at=_now_from_trace(trace_store),
                source_packet_id=read_packet.packet_id,
                failure_stage=f"R2:step_{step_index:04d}",
                failure_type=r2_result.failure_type,
                failure_reason=r2_result.validation.error or "R2 payload validation failed.",
                source_data_ids=_unique_strings(
                    [
                        *base_source_data_ids,
                        r1.frame_id,
                        candidate_layer_surface.frame_id,
                        r2_result.call_data_id,
                    ]
                ),
                source_trace_ids=_unique_strings([*source_trace_ids, *trace_event_ids, r2_result.trace_event_id]),
                llm_call_data_ids=llm_call_data_ids,
                r1_goal_frame_id=r1.frame_id,
                output_data_ids=output_data_ids,
                failure_payload_summary=_r2_failure_payload_summary(
                    r2_result.validation.payload,
                    available_graph_node_ids=available_graph_node_ids,
                    candidate_layer_surface=candidate_layer_surface,
                ),
                candidate_layer_surfaces=candidate_layer_surfaces,
                surface_selections=surface_selections,
                r2_selections=r2_selections,
                r3_inspections=r3_inspections,
                graph_surfaces=graph_surfaces,
                continuations=continuations,
            )

        surface_selection = _surface_selection_frame_from_payload(
            payload=r2_result.validation.payload,
            frame_label=step_label,
            r1=r1,
            candidate_layer_surface=candidate_layer_surface,
            model_id=r2_result.model_id,
            llm_call_data_id=r2_result.call_data_id,
            source_trace_ids=_unique_strings([*source_trace_ids, r2_result.trace_event_id]),
        )
        surface_selections.append(surface_selection)
        _record_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            actor="R2:surface",
            data_type=R_LOOP_VESSEL_SURFACE_SELECTION_DATA_TYPE,
            frame_id=surface_selection.frame_id,
            payload=asdict(surface_selection),
            input_ref=_unique_strings([*source_trace_ids, r2_result.trace_event_id]),
            trace_event_ids=trace_event_ids,
            output_data_ids=output_data_ids,
        )

        r2 = _r2_frame_from_payload(
            payload=r2_result.validation.payload,
            frame_label=step_label,
            read_packet=read_packet,
            r1=r1,
            candidate_layer_surface=candidate_layer_surface,
            available_graph_node_ids=_surface_candidate_ids_for_selection(
                candidate_layer_surface,
                surface_selection.selected_surface_id,
                fallback_graph_node_ids=available_graph_node_ids,
            ),
            model_id=r2_result.model_id,
            llm_call_data_id=r2_result.call_data_id,
            source_trace_ids=_unique_strings([*source_trace_ids, r2_result.trace_event_id]),
        )
        r2_selections.append(r2)
        _record_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            actor="R2",
            data_type="node_output:R2_graph_node_selection_frame",
            frame_id=r2.frame_id,
            payload=asdict(r2),
            input_ref=_unique_strings([*source_trace_ids, r2_result.trace_event_id]),
            trace_event_ids=trace_event_ids,
            output_data_ids=output_data_ids,
        )

        if r2.selection_status != "selected" or r2.selected_graph_node_id is None:
            final_budget = _traverse_budget_frame(r1=r1, frame_label=frame_label, step_index=step_index)
            return_summary = _return_summary_for_traverse(
                frame_label=frame_label,
                read_packet=read_packet,
                r1=r1,
                final_budget=final_budget,
                r2_selections=r2_selections,
                r3_inspections=r3_inspections,
                final_continuation=None,
                forced_status="partial",
                forced_continuation_status="stop_no_actionable_path",
            )
            break

        selected_record = _selected_candidate_record(read_packet, r2.selected_graph_node_id)
        selected_is_terminal_material = _is_terminal_material_record(selected_record)
        selected_is_raw_original_material = _is_raw_original_material_record(selected_record)
        r3_result = executor.run(
            node_id=R3_VESSEL_NODE_ID,
            prompt=_prompt(R3_VESSEL_INSPECTOR_PROMPT_REF),
            input_payload=_r3_input_payload(
                user_question=user_question,
                r1=r1,
                r2=r2,
                selected_record=selected_record,
            ),
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            prompt_ref=R3_VESSEL_INSPECTOR_PROMPT_REF,
            input_ref=_unique_strings([*source_trace_ids, *trace_event_ids]),
            source_data_ids=[
                *base_source_data_ids,
                r1.frame_id,
                r2.frame_id,
                r2.selected_graph_node_id,
            ],
            payload_validator=_validate_r3_payload,
        )
        _append_llm_refs(r3_result, llm_call_data_ids, trace_event_ids)
        if r3_result.failure_type != "none" or r3_result.validation.payload is None:
            return _record_traverse_failure_result(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                frame_id=result_frame_id,
                created_at=_now_from_trace(trace_store),
                source_packet_id=read_packet.packet_id,
                failure_stage=f"R3:step_{step_index:04d}",
                failure_type=r3_result.failure_type,
                failure_reason=r3_result.validation.error or "R3 payload validation failed.",
                source_data_ids=_unique_strings(
                    [
                        *base_source_data_ids,
                        r1.frame_id,
                        candidate_layer_surface.frame_id,
                        r2.frame_id,
                        r3_result.call_data_id,
                    ]
                ),
                source_trace_ids=_unique_strings([*source_trace_ids, *trace_event_ids, r3_result.trace_event_id]),
                llm_call_data_ids=llm_call_data_ids,
                r1_goal_frame_id=r1.frame_id,
                output_data_ids=output_data_ids,
                candidate_layer_surfaces=candidate_layer_surfaces,
                surface_selections=surface_selections,
                r2_selections=r2_selections,
                r3_inspections=r3_inspections,
                graph_surfaces=graph_surfaces,
                continuations=continuations,
            )

        r3 = _r3_frame_from_payload(
            payload=r3_result.validation.payload,
            frame_label=step_label,
            selected_record=selected_record,
            read_packet=read_packet,
            r2=r2,
            model_id=r3_result.model_id,
            llm_call_data_id=r3_result.call_data_id,
            source_trace_ids=_unique_strings([*source_trace_ids, r3_result.trace_event_id]),
        )
        r3_inspections.append(r3)
        if selected_is_terminal_material:
            terminal_material_seen_count += 1
        if selected_is_raw_original_material:
            raw_original_material_seen_count += 1
            raw_original_read_cap_reached = (
                raw_original_material_seen_count >= max_raw_original_material_reads
            )
        _record_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            actor="R3",
            data_type="node_output:R3_graph_inspection_frame",
            frame_id=r3.frame_id,
            payload=asdict(r3),
            input_ref=_unique_strings([*source_trace_ids, r3_result.trace_event_id]),
            trace_event_ids=trace_event_ids,
            output_data_ids=output_data_ids,
        )

        graph_surface = _graph_traversal_candidate_surface_frame(
            frame_label=step_label,
            r3=r3,
            selected_record=selected_record,
        )
        graph_surfaces.append(graph_surface)
        _record_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            actor="R:graph_traversal_candidate_surface",
            data_type="node_output:R_graph_traversal_candidate_surface_frame",
            frame_id=graph_surface.frame_id,
            payload=asdict(graph_surface),
            input_ref=[r3.frame_id],
            trace_event_ids=trace_event_ids,
            output_data_ids=output_data_ids,
        )

        final_budget = _traverse_budget_frame(
            r1=r1,
            frame_label=frame_label,
            step_index=step_index,
        )
        _record_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            actor="R:budget",
            data_type="node_output:R_loop_budget_frame",
            frame_id=final_budget.frame_id,
            payload=asdict(final_budget),
            input_ref=[r1.frame_id, r3.frame_id],
            trace_event_ids=trace_event_ids,
            output_data_ids=output_data_ids,
        )

        final_continuation = decide_r_loop_continuation(
            frame_id=f"R:{step_label}:vessel_traverse_continuation_frame",
            r3_inspection=r3,
            budget=final_budget,
            source_trace_ids=_unique_strings([*source_trace_ids, *trace_event_ids]),
        )
        if _should_force_deeper_for_terminal_material(
            continuation=final_continuation,
            graph_surface=graph_surface,
            terminal_material_seen_count=terminal_material_seen_count,
            min_terminal_material_count=R_TRAVERSE_MIN_TERMINAL_MATERIAL_READS,
        ):
            final_continuation = _terminal_material_guard_continuation_frame(
                frame_id=final_continuation.frame_id,
                r3=r3,
                budget=final_budget,
                source_trace_ids=_unique_strings([*source_trace_ids, *trace_event_ids]),
            )
            early_stop_guard_trigger_count += 1
        if _should_stop_for_raw_original_cap(
            continuation=final_continuation,
            raw_original_material_seen_count=raw_original_material_seen_count,
            max_raw_original_material_count=max_raw_original_material_reads,
        ):
            final_continuation = _raw_original_cap_continuation_frame(
                frame_id=final_continuation.frame_id,
                r3=r3,
                budget=final_budget,
                source_trace_ids=_unique_strings([*source_trace_ids, *trace_event_ids]),
            )
            raw_original_read_cap_reached = True
        continuations.append(final_continuation)
        _record_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            actor="R:continuation",
            data_type="node_output:R_loop_continuation_frame",
            frame_id=final_continuation.frame_id,
            payload=asdict(final_continuation),
            input_ref=[r3.frame_id, final_budget.frame_id],
            trace_event_ids=trace_event_ids,
            output_data_ids=output_data_ids,
        )

        if final_continuation.continuation_status == "continue_deeper":
            next_candidate_surface = _candidate_layer_surface_frame_from_graph_surface(
                frame_label=f"{frame_label}_step_{step_index + 1:04d}",
                read_packet=read_packet,
                graph_surface=graph_surface,
                created_at=_now_from_trace(trace_store),
            )
            if next_candidate_surface.total_candidate_count <= 0:
                return_summary = _return_summary_for_traverse(
                    frame_label=frame_label,
                    read_packet=read_packet,
                    r1=r1,
                    final_budget=final_budget,
                    r2_selections=r2_selections,
                    r3_inspections=r3_inspections,
                    final_continuation=final_continuation,
                    forced_status="partial",
                    forced_continuation_status="stop_no_actionable_path",
                )
                break
            continue

        return_summary = _return_summary_for_traverse(
            frame_label=frame_label,
            read_packet=read_packet,
            r1=r1,
            final_budget=final_budget,
            r2_selections=r2_selections,
            r3_inspections=r3_inspections,
            final_continuation=final_continuation,
        )
        break

    if return_summary is None:
        final_budget = final_budget or _traverse_budget_frame(
            r1=r1,
            frame_label=frame_label,
            step_index=max_node_reads,
        )
        return_summary = _return_summary_for_traverse(
            frame_label=frame_label,
            read_packet=read_packet,
            r1=r1,
            final_budget=final_budget,
            r2_selections=r2_selections,
            r3_inspections=r3_inspections,
            final_continuation=final_continuation,
            forced_status="partial",
            forced_continuation_status="stop_budget_exhausted",
        )

    _record_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        actor="R:return_summary",
        data_type="node_output:R_loop_return_summary_frame",
        frame_id=return_summary.frame_id,
        payload=asdict(return_summary),
        input_ref=[continuations[-1].frame_id] if continuations else [r1.frame_id],
        trace_event_ids=trace_event_ids,
        output_data_ids=output_data_ids,
    )

    result_frame = _traverse_result_frame(
        frame_id=result_frame_id,
        created_at=_now_from_trace(trace_store),
        traverse_status="completed",
        source_packet_id=read_packet.packet_id,
        r1=r1,
        final_budget=final_budget,
        return_summary=return_summary,
        candidate_layer_surfaces=candidate_layer_surfaces,
        graph_surfaces=graph_surfaces,
        r2_selections=r2_selections,
        r3_inspections=r3_inspections,
        continuations=continuations,
        llm_call_data_ids=llm_call_data_ids,
        output_data_ids=output_data_ids,
        source_data_ids=base_source_data_ids,
        source_trace_ids=_unique_strings([*source_trace_ids, *trace_event_ids]),
        terminal_material_seen_count=terminal_material_seen_count,
        min_terminal_material_count=R_TRAVERSE_MIN_TERMINAL_MATERIAL_READS,
        raw_original_material_seen_count=raw_original_material_seen_count,
        max_raw_original_material_count=max_raw_original_material_reads,
        raw_original_read_cap_reached=raw_original_read_cap_reached,
        early_stop_guard_trigger_count=early_stop_guard_trigger_count,
    )
    _record_traverse_result_frame(
        trace_store,
        data_store,
        turn_id,
        result_frame,
        trace_event_ids,
        output_data_ids,
    )
    return RLoopVesselTraverseRun(
        result_frame=result_frame,
        r1_goal=r1,
        final_budget=final_budget,
        r2_selections=r2_selections,
        r3_inspections=r3_inspections,
        continuations=continuations,
        return_summary=return_summary,
        candidate_layer_surfaces=candidate_layer_surfaces,
        surface_selections=surface_selections,
        graph_traversal_candidate_surfaces=graph_surfaces,
        trace_event_ids=trace_event_ids,
        output_data_ids=output_data_ids,
    )


def _r1_input_payload(
    *,
    user_question: str,
    read_packet: RLoopVesselReadPacketFrame,
    policy_name: str = "one_step",
    max_traversal_depth: int = R_ONE_STEP_MAX_TRAVERSAL_DEPTH,
    max_branch_switches: int = R_ONE_STEP_MAX_BRANCH_SWITCHES,
    max_node_reads: int = R_ONE_STEP_MAX_NODE_READS,
    max_context_tokens: int = R_ONE_STEP_MAX_CONTEXT_TOKENS,
) -> dict[str, object]:
    # R1 is a goal setter. Candidate text belongs to R2/R3, not to R1.
    anchor_id = _user_question_anchor_id(user_question)
    return {
        "user_question": user_question,
        "user_question_anchor": {
            "anchor_id": anchor_id,
            "source_field": "user_question",
            "copy_required": True,
        },
        "read_packet_id": read_packet.packet_id,
        "entry_candidate_count": read_packet.entry_candidate_count,
        "summary_candidate_count": read_packet.summary_candidate_count,
        "summary_count_by_data_kind": read_packet.summary_count_by_data_kind,
        "summary_count_by_depth": read_packet.summary_count_by_depth,
        "traversal_policy": {
            "policy_name": policy_name,
            "max_traversal_depth": max_traversal_depth,
            "max_branch_switches": max_branch_switches,
            "max_node_reads": max_node_reads,
            "max_context_tokens": max_context_tokens,
        },
        "candidate_text_visibility_policy": (
            "R1 does not receive candidate IDs, summary text, or summary previews. "
            "R1 must copy user_question_anchor.anchor_id exactly into user_question_anchor_id "
            "and set graph_search_goal from the user question plus packet-level counts only."
        ),
        "source_data_ids": [read_packet.packet_id],
    }


def _r2_input_payload(
    *,
    user_question: str,
    read_packet: RLoopVesselReadPacketFrame,
    r1: R1GraphGoalFrame,
    candidate_layer_surface: RLoopVesselCandidateLayerSurfaceFrame,
    available_graph_node_ids: list[str],
    current_graph_node_id: str = "graph:core_ego:root",
    traversal_policy: str = "core_ego_direct_entry_candidates_only",
) -> dict[str, object]:
    selection_ref_map = _r2_selection_ref_map(read_packet, candidate_layer_surface)
    return {
        "user_question": user_question,
        "r1_goal": asdict(r1),
        "read_packet_id": read_packet.packet_id,
        "candidate_layer_surface_ref_records": selection_ref_map["surface_records"],
        "available_surface_refs": selection_ref_map["available_surface_refs"],
        "candidate_records_by_surface_ref": selection_ref_map["candidate_records_by_surface_ref"],
        "selection_ref_contract": {
            "surface_output_field": "selected_surface_ref",
            "node_output_field": "selected_node_ref",
            "surface_ref_source": "available_surface_refs",
            "node_ref_source": "candidate_records_by_surface_ref[*][*].node_ref",
            "actual_graph_ids_hidden_from_r2": True,
            "current_graph_node_id": current_graph_node_id,
            "first_step_policy": traversal_policy,
        },
        "source_data_ids": [read_packet.packet_id, r1.frame_id, candidate_layer_surface.frame_id],
    }


def _r3_input_payload(
    *,
    user_question: str,
    r1: R1GraphGoalFrame,
    r2: R2GraphNodeSelectionFrame,
    selected_record: dict[str, object],
) -> dict[str, object]:
    return {
        "user_question": user_question,
        "r1_goal": asdict(r1),
        "r2_selection": asdict(r2),
        "selected_candidate_record": selected_record,
        "known_child_node_ids": _candidate_child_node_ids(selected_record),
        "hierarchy_child_candidate_records": _hierarchy_child_candidate_record_views(selected_record),
        "hierarchy_child_candidate_count": len(_candidate_child_node_ids(selected_record)),
        "hierarchy_read_policy": {
            "child_candidates_generated_by": "CODE:R_VESSEL_HIERARCHY_CHILD_CANDIDATE_BUILDER",
            "child_candidates_info_class": "absolute",
            "llm_may_judge_sufficiency": True,
            "llm_must_not_invent_child_ids": True,
        },
        "source_data_ids": [r1.frame_id, r2.frame_id, _record_node_id(selected_record)],
    }


def _summary_candidate_view(records: list[dict[str, object]]) -> list[dict[str, object]]:
    view: list[dict[str, object]] = []
    for record in records:
        view.append(_summary_candidate_record_view(record))
    return view


def _summary_candidate_record_view(record: dict[str, object]) -> dict[str, object]:
    return {
        "summary_display_name": record.get("summary_display_name"),
        "data_kind": record.get("data_kind"),
        "branch_role": _branch_role_for_record(record),
        "summary_depth": record.get("summary_depth"),
        "info_class": record.get("info_class"),
        "target_display_name": record.get("target_display_name"),
        "target_node_kind": record.get("target_node_kind"),
        "source_leaf_count": record.get("source_leaf_count"),
        "source_summary_count": record.get("source_summary_count"),
        "summary_text": record.get("summary_text"),
        "summary_text_char_count": record.get("summary_text_char_count"),
    }


def _validate_r1_payload(
    payload: dict[str, object],
    *,
    read_packet: RLoopVesselReadPacketFrame,
    user_question: str,
) -> None:
    granularity = _payload_text(payload, "required_information_granularity")
    if granularity not in {"raw", "low_summary", "medium_summary", "high_summary", "unknown"}:
        raise ValueError("R1 required_information_granularity is invalid")
    allowed_depth = _payload_int(payload, "allowed_summary_depth")
    if allowed_depth < 0:
        raise ValueError("R1 allowed_summary_depth must not be negative")
    max_seen_depth = _max_summary_depth(read_packet)
    if max_seen_depth is not None and allowed_depth > max_seen_depth:
        raise ValueError("R1 allowed_summary_depth must not exceed supplied summary depth")
    if not _payload_text(payload, "graph_search_goal"):
        raise ValueError("R1 graph_search_goal must not be empty")
    if not _payload_text(payload, "stop_condition"):
        raise ValueError("R1 stop_condition must not be empty")
    expected_anchor_id = _user_question_anchor_id(user_question)
    if _payload_text(payload, "user_question_anchor_id") != expected_anchor_id:
        raise ValueError("R1 user_question_anchor_id must copy the supplied user question anchor")


def _validate_r2_payload(
    payload: dict[str, object],
    *,
    available_graph_node_ids: list[str],
    candidate_layer_surface: RLoopVesselCandidateLayerSurfaceFrame,
) -> None:
    selection_ref_map = _r2_selection_ref_map_from_surface(candidate_layer_surface)
    status = _payload_text(payload, "selection_status")
    if status not in {"selected", "none_selected"}:
        raise ValueError("R2 selection_status must be selected or none_selected")
    selected_surface_ref = _selected_surface_ref_from_r2_payload(payload)
    selected_node_ref = _selected_node_ref_from_r2_payload(payload)
    selected_surface_id = _selected_surface_id_from_r2_payload(
        payload,
        selection_ref_map=selection_ref_map,
    )
    selected_id = _selected_graph_node_id_from_r2_payload(
        payload,
        selection_ref_map=selection_ref_map,
    )
    if status == "selected":
        if selected_surface_ref is not None and selected_surface_id is None:
            raise ValueError("R2 selected_surface_ref must be in available_surface_refs")
        if selected_node_ref is not None and selected_id is None:
            raise ValueError("R2 selected_node_ref must be in available_node_refs")
        if not isinstance(selected_surface_id, str) or not selected_surface_id:
            raise ValueError("selected R2 payload must include selected_surface_ref")
        if selected_surface_id not in candidate_layer_surface.available_surface_ids:
            raise ValueError("R2 selected_surface_id must be in available_surface_ids")
        if not isinstance(selected_id, str) or not selected_id:
            raise ValueError("selected R2 payload must include selected_node_ref")
        if selected_id not in available_graph_node_ids:
            raise ValueError("R2 selected_graph_node_id must be in available_graph_node_ids")
        surface_candidate_ids = _surface_candidate_ids(candidate_layer_surface, selected_surface_id)
        if selected_id not in surface_candidate_ids:
            raise ValueError("R2 selected_graph_node_id must belong to selected_surface_id")
    elif selected_id is not None or selected_node_ref is not None:
        raise ValueError("none_selected R2 payload must set selected_node_ref to null")
    elif selected_surface_id is not None or selected_surface_ref is not None:
        raise ValueError("none_selected R2 payload must set selected_surface_ref to null")
    granularity = _payload_text(payload, "expected_information_granularity")
    if granularity not in {"raw", "low_summary", "medium_summary", "high_summary", "unknown"}:
        raise ValueError("R2 expected_information_granularity is invalid")
    if not _payload_text(payload, "selection_reason"):
        raise ValueError("R2 selection_reason must not be empty")
    if not _payload_text(payload, "expected_source_kind"):
        raise ValueError("R2 expected_source_kind must not be empty")


def _validate_r3_payload(payload: dict[str, object]) -> None:
    if _payload_text(payload, "current_information_granularity") not in {
        "raw",
        "low_summary",
        "medium_summary",
        "high_summary",
        "unknown",
    }:
        raise ValueError("R3 current_information_granularity is invalid")
    if _payload_text(payload, "sufficiency_status") not in {
        "sufficient",
        "insufficient",
        "unknown",
    }:
        raise ValueError("R3 sufficiency_status is invalid")
    if _payload_text(payload, "granularity_problem_status") not in {
        "none",
        "needs_lower_granularity",
        "unknown",
    }:
        raise ValueError("R3 granularity_problem_status is invalid")
    if _payload_text(payload, "branch_problem_status") not in {
        "none",
        "wrong_branch",
        "unknown",
    }:
        raise ValueError("R3 branch_problem_status is invalid")
    if _payload_text(payload, "recommended_next_action") not in {
        "stop",
        "deeper",
        "switch_branch",
        "fail",
    }:
        raise ValueError("R3 recommended_next_action is invalid")
    if not _payload_text(payload, "inspection_reason"):
        raise ValueError("R3 inspection_reason must not be empty")


def _r2_failure_payload_summary(
    payload: dict[str, object] | None,
    *,
    available_graph_node_ids: list[str],
    candidate_layer_surface: RLoopVesselCandidateLayerSurfaceFrame,
) -> dict[str, object] | None:
    if not isinstance(payload, dict):
        return None
    selection_ref_map = _r2_selection_ref_map_from_surface(candidate_layer_surface)
    selected_surface_ref = _selected_surface_ref_from_r2_payload(payload)
    selected_node_ref = _selected_node_ref_from_r2_payload(payload)
    selected_surface_id = _selected_surface_id_from_r2_payload(
        payload,
        selection_ref_map=selection_ref_map,
    )
    selected_graph_node_id = _selected_graph_node_id_from_r2_payload(
        payload,
        selection_ref_map=selection_ref_map,
    )
    surface_candidate_ids = _surface_candidate_ids(
        candidate_layer_surface,
        selected_surface_id,
    )
    available_surface_refs = selection_ref_map.get("available_surface_refs")
    node_ref_to_graph_node_id = selection_ref_map.get("node_ref_to_graph_node_id")
    return {
        "selection_status": payload.get("selection_status"),
        "selected_surface_ref": selected_surface_ref,
        "selected_node_ref": selected_node_ref,
        "selected_surface_id": selected_surface_id,
        "selected_graph_node_id": selected_graph_node_id,
        "selected_surface_ref_in_available": selected_surface_ref in available_surface_refs
        if isinstance(available_surface_refs, list) and selected_surface_ref is not None
        else False,
        "selected_node_ref_in_available": selected_node_ref in node_ref_to_graph_node_id
        if isinstance(node_ref_to_graph_node_id, dict) and selected_node_ref is not None
        else False,
        "selected_surface_id_in_available": selected_surface_id
        in candidate_layer_surface.available_surface_ids
        if selected_surface_id is not None
        else False,
        "selected_graph_node_id_in_available": selected_graph_node_id
        in available_graph_node_ids
        if selected_graph_node_id is not None
        else False,
        "selected_graph_node_id_in_selected_surface": selected_graph_node_id
        in surface_candidate_ids
        if selected_graph_node_id is not None
        else False,
        "selected_surface_candidate_count": len(surface_candidate_ids),
    }


def _r1_frame_from_payload(
    *,
    payload: dict[str, object],
    frame_label: str,
    read_packet: RLoopVesselReadPacketFrame,
    model_id: str,
    llm_call_data_id: str | None,
    source_trace_ids: list[str],
    max_traversal_depth: int = R_ONE_STEP_MAX_TRAVERSAL_DEPTH,
    max_branch_switches: int = R_ONE_STEP_MAX_BRANCH_SWITCHES,
    max_node_reads: int = R_ONE_STEP_MAX_NODE_READS,
    max_context_tokens: int = R_ONE_STEP_MAX_CONTEXT_TOKENS,
) -> R1GraphGoalFrame:
    frame = R1GraphGoalFrame(
        frame_id=f"R1:{frame_label}:vessel_goal_frame",
        graph_search_goal=_payload_text(payload, "graph_search_goal"),
        required_information_granularity=_payload_text(payload, "required_information_granularity"),
        allowed_summary_depth=_payload_int(payload, "allowed_summary_depth"),
        max_traversal_depth=max_traversal_depth,
        max_branch_switches=max_branch_switches,
        max_node_reads=max_node_reads,
        max_context_tokens=max_context_tokens,
        stop_condition=_payload_text(payload, "stop_condition"),
        source_graph_guide_packet_id=read_packet.packet_id,
        user_question_anchor_id=_payload_text(payload, "user_question_anchor_id"),
        source_data_ids=_unique_strings([read_packet.packet_id, llm_call_data_id]),
        source_trace_ids=source_trace_ids,
        generated_by=f"LLM:{model_id}:R1_vessel_goal_setter",
        info_class="mixed",
        semantic_judgement_status="ran",
    )
    validate_r1_graph_goal_frame(frame)
    return frame


def _budget_frame(*, r1: R1GraphGoalFrame, frame_label: str) -> RLoopBudgetFrame:
    frame = RLoopBudgetFrame(
        frame_id=f"R:{frame_label}:vessel_one_step_budget_frame",
        source_r1_goal_frame_id=r1.frame_id,
        max_traversal_depth=r1.max_traversal_depth,
        max_branch_switches=r1.max_branch_switches,
        max_node_reads=r1.max_node_reads,
        max_context_tokens=r1.max_context_tokens,
        used_traversal_depth=0,
        used_branch_switches=0,
        used_node_reads=1,
        used_context_tokens=0,
        budget_status="within_budget",
        source_data_ids=[r1.frame_id],
        source_trace_ids=list(r1.source_trace_ids),
        generated_by=R_LOOP_VESSEL_ONE_STEP_GENERATOR,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )
    validate_r_loop_budget_frame(frame)
    return frame


def _traverse_budget_frame(
    *,
    r1: R1GraphGoalFrame,
    frame_label: str,
    step_index: int,
) -> RLoopBudgetFrame:
    safe_step = max(0, step_index)
    frame = RLoopBudgetFrame(
        frame_id=f"R:{frame_label}:vessel_traverse_budget_frame:{safe_step:04d}",
        source_r1_goal_frame_id=r1.frame_id,
        max_traversal_depth=r1.max_traversal_depth,
        max_branch_switches=r1.max_branch_switches,
        max_node_reads=r1.max_node_reads,
        max_context_tokens=r1.max_context_tokens,
        used_traversal_depth=safe_step,
        used_branch_switches=0,
        used_node_reads=safe_step,
        used_context_tokens=0,
        budget_status="within_budget",
        source_data_ids=[r1.frame_id],
        source_trace_ids=list(r1.source_trace_ids),
        generated_by=R_LOOP_VESSEL_TRAVERSE_GENERATOR,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )
    validate_r_loop_budget_frame(frame)
    return frame


def _should_force_deeper_for_terminal_material(
    *,
    continuation: RLoopContinuationFrame,
    graph_surface: RGraphTraversalCandidateSurfaceFrame,
    terminal_material_seen_count: int,
    min_terminal_material_count: int,
) -> bool:
    if continuation.continuation_status != "stop_sufficient":
        return False
    if terminal_material_seen_count >= min_terminal_material_count:
        return False
    if graph_surface.candidate_count <= 0:
        return False
    if continuation.remaining_node_reads <= 0:
        return False
    if continuation.remaining_traversal_depth <= 0:
        return False
    if continuation.remaining_context_tokens <= 0:
        return False
    return True


def _terminal_material_guard_continuation_frame(
    *,
    frame_id: str,
    r3: R3GraphInspectionFrame,
    budget: RLoopBudgetFrame,
    source_trace_ids: list[str],
) -> RLoopContinuationFrame:
    remaining_traversal_depth = max(
        budget.max_traversal_depth - budget.used_traversal_depth,
        0,
    )
    remaining_branch_switches = max(
        budget.max_branch_switches - budget.used_branch_switches,
        0,
    )
    remaining_node_reads = max(budget.max_node_reads - budget.used_node_reads, 0)
    remaining_context_tokens = max(
        budget.max_context_tokens - budget.used_context_tokens,
        0,
    )
    frame = RLoopContinuationFrame(
        frame_id=frame_id,
        source_r3_inspection_frame_id=r3.frame_id,
        source_budget_frame_id=budget.frame_id,
        continuation_status="continue_deeper",
        continuation_reason_code="CODE_STATUS:r_loop_terminal_material_not_seen",
        next_target_node="R2",
        remaining_traversal_depth=remaining_traversal_depth,
        remaining_branch_switches=remaining_branch_switches,
        remaining_node_reads=remaining_node_reads,
        remaining_context_tokens=remaining_context_tokens,
        source_data_ids=_unique_strings(
            [
                r3.frame_id,
                budget.frame_id,
                *r3.source_data_ids,
                *budget.source_data_ids,
            ]
        ),
        source_trace_ids=_unique_strings(
            [
                *source_trace_ids,
                *r3.source_trace_ids,
                *budget.source_trace_ids,
            ]
        ),
    )
    validate_r_loop_continuation_frame(frame)
    return frame


def _should_stop_for_raw_original_cap(
    *,
    continuation: RLoopContinuationFrame,
    raw_original_material_seen_count: int,
    max_raw_original_material_count: int,
) -> bool:
    if raw_original_material_seen_count < max_raw_original_material_count:
        return False
    return continuation.continuation_status in {
        "continue_deeper",
        "continue_switch_branch",
    }


def _raw_original_cap_continuation_frame(
    *,
    frame_id: str,
    r3: R3GraphInspectionFrame,
    budget: RLoopBudgetFrame,
    source_trace_ids: list[str],
) -> RLoopContinuationFrame:
    remaining_traversal_depth = max(
        budget.max_traversal_depth - budget.used_traversal_depth,
        0,
    )
    remaining_branch_switches = max(
        budget.max_branch_switches - budget.used_branch_switches,
        0,
    )
    remaining_node_reads = max(budget.max_node_reads - budget.used_node_reads, 0)
    remaining_context_tokens = max(
        budget.max_context_tokens - budget.used_context_tokens,
        0,
    )
    frame = RLoopContinuationFrame(
        frame_id=frame_id,
        source_r3_inspection_frame_id=r3.frame_id,
        source_budget_frame_id=budget.frame_id,
        continuation_status="stop_budget_exhausted",
        continuation_reason_code="CODE_STATUS:r_loop_raw_original_read_cap_reached",
        next_target_node="return_summary",
        remaining_traversal_depth=remaining_traversal_depth,
        remaining_branch_switches=remaining_branch_switches,
        remaining_node_reads=remaining_node_reads,
        remaining_context_tokens=remaining_context_tokens,
        source_data_ids=_unique_strings(
            [
                r3.frame_id,
                budget.frame_id,
                *r3.source_data_ids,
                *budget.source_data_ids,
            ]
        ),
        source_trace_ids=_unique_strings(
            [
                *source_trace_ids,
                *r3.source_trace_ids,
                *budget.source_trace_ids,
            ]
        ),
    )
    validate_r_loop_continuation_frame(frame)
    return frame


def _surface_selection_frame_from_payload(
    *,
    payload: dict[str, object],
    frame_label: str,
    r1: R1GraphGoalFrame,
    candidate_layer_surface: RLoopVesselCandidateLayerSurfaceFrame,
    model_id: str,
    llm_call_data_id: str | None,
    source_trace_ids: list[str],
) -> RLoopVesselSurfaceSelectionFrame:
    selected_surface_id = _selected_surface_id_from_r2_payload(
        payload,
        selection_ref_map=_r2_selection_ref_map_from_surface(candidate_layer_surface),
    )
    frame = RLoopVesselSurfaceSelectionFrame(
        frame_id=f"R2:{frame_label}:vessel_surface_selection_frame",
        selection_scope="r_loop_vessel_candidate_layer_surface",
        available_surface_ids=list(candidate_layer_surface.available_surface_ids),
        selection_status=_payload_text(payload, "selection_status"),
        selected_surface_id=selected_surface_id,
        selected_surface_candidate_count=len(
            _surface_candidate_ids(candidate_layer_surface, selected_surface_id)
        )
        if selected_surface_id
        else 0,
        surface_selection_reason=_payload_text(payload, "selection_reason"),
        source_r1_goal_frame_id=r1.frame_id,
        source_surface_frame_id=candidate_layer_surface.frame_id,
        source_data_ids=_unique_strings(
            [candidate_layer_surface.frame_id, r1.frame_id, llm_call_data_id]
        ),
        source_trace_ids=source_trace_ids,
        generated_by=f"LLM:{model_id}:R2_vessel_node_selector",
    )
    _validate_surface_selection_frame(frame)
    return frame


def _r2_frame_from_payload(
    *,
    payload: dict[str, object],
    frame_label: str,
    read_packet: RLoopVesselReadPacketFrame,
    r1: R1GraphGoalFrame,
    candidate_layer_surface: RLoopVesselCandidateLayerSurfaceFrame,
    available_graph_node_ids: list[str],
    model_id: str,
    llm_call_data_id: str | None,
    source_trace_ids: list[str],
) -> R2GraphNodeSelectionFrame:
    selected_id = _selected_graph_node_id_from_r2_payload(
        payload,
        selection_ref_map=_r2_selection_ref_map_from_surface(candidate_layer_surface),
    )
    frame = R2GraphNodeSelectionFrame(
        frame_id=f"R2:{frame_label}:vessel_node_selection_frame",
        selection_scope="r_loop_vessel_read_packet",
        available_graph_node_ids=available_graph_node_ids,
        selection_status=_payload_text(payload, "selection_status"),
        selected_graph_node_id=selected_id if isinstance(selected_id, str) else None,
        selection_reason=_payload_text(payload, "selection_reason"),
        expected_information_granularity=_payload_text(payload, "expected_information_granularity"),
        expected_source_kind=_payload_text(payload, "expected_source_kind"),
        source_r1_goal_frame_id=r1.frame_id,
        source_data_ids=_unique_strings([read_packet.packet_id, r1.frame_id, llm_call_data_id]),
        source_trace_ids=source_trace_ids,
        generated_by=f"LLM:{model_id}:R2_vessel_node_selector",
        info_class="mixed",
        semantic_judgement_status="ran",
    )
    validate_r2_graph_node_selection_frame(frame)
    return frame


def _r3_frame_from_payload(
    *,
    payload: dict[str, object],
    frame_label: str,
    selected_record: dict[str, object],
    read_packet: RLoopVesselReadPacketFrame,
    r2: R2GraphNodeSelectionFrame,
    model_id: str,
    llm_call_data_id: str | None,
    source_trace_ids: list[str],
) -> R3GraphInspectionFrame:
    selected_node_id = _record_node_id(selected_record)
    child_node_ids = _candidate_child_node_ids(selected_record)
    frame = R3GraphInspectionFrame(
        frame_id=f"R3:{frame_label}:vessel_inspection_frame",
        inspected_graph_node_id=selected_node_id,
        node_kind=_candidate_node_kind(selected_record),
        child_node_count=len(child_node_ids),
        child_node_ids=child_node_ids,
        summary_depth=_candidate_summary_depth(selected_record),
        source_leaf_count=_candidate_source_leaf_count(selected_record),
        current_information_granularity=_payload_text(payload, "current_information_granularity"),
        sufficiency_status=_payload_text(payload, "sufficiency_status"),
        granularity_problem_status=_payload_text(payload, "granularity_problem_status"),
        branch_problem_status=_payload_text(payload, "branch_problem_status"),
        recommended_next_action=_payload_text(payload, "recommended_next_action"),
        inspection_reason=_payload_text(payload, "inspection_reason"),
        source_r2_selection_frame_id=r2.frame_id,
        source_data_ids=_unique_strings([read_packet.packet_id, r2.frame_id, selected_node_id, llm_call_data_id]),
        source_trace_ids=source_trace_ids,
        generated_by=f"LLM:{model_id}:R3_vessel_inspector",
        info_class="mixed",
        semantic_judgement_status="ran",
    )
    validate_r3_graph_inspection_frame(frame)
    return frame


def _graph_traversal_candidate_surface_frame(
    *,
    frame_label: str,
    r3: R3GraphInspectionFrame,
    selected_record: dict[str, object],
) -> RGraphTraversalCandidateSurfaceFrame:
    child_candidate_node_ids = _unique_strings(list(r3.child_node_ids))
    candidate_records = [
        {
            "candidate_node_id": child_id,
            "relation": "child",
            "source_id": r3.frame_id,
            "source_field": "hierarchy_child_node_ids",
        }
        for child_id in child_candidate_node_ids
    ]
    source_data_ids = _unique_strings(
        [
            r3.frame_id,
            r3.inspected_graph_node_id,
            *child_candidate_node_ids,
            *_hierarchy_child_record_source_ids(selected_record),
        ]
    )
    frame = RGraphTraversalCandidateSurfaceFrame(
        frame_id=f"R:{frame_label}:vessel_graph_traversal_candidate_surface_frame",
        source_r3_inspection_frame_id=r3.frame_id,
        inspected_graph_node_id=r3.inspected_graph_node_id,
        child_candidate_node_ids=child_candidate_node_ids,
        next_candidate_node_ids=[],
        previous_candidate_node_ids=[],
        candidate_graph_node_ids=child_candidate_node_ids,
        candidate_records=candidate_records,
        candidate_count=len(child_candidate_node_ids),
        source_data_ids=source_data_ids,
        source_trace_ids=list(r3.source_trace_ids),
    )
    validate_r_graph_traversal_candidate_surface_frame(frame)
    return frame


def _hierarchy_child_record_source_ids(selected_record: dict[str, object]) -> list[str]:
    records = selected_record.get("hierarchy_child_candidate_records")
    if not isinstance(records, list):
        return []
    source_ids: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        candidate_id = record.get("candidate_node_id")
        if isinstance(candidate_id, str):
            source_ids.append(candidate_id)
    return _unique_strings(source_ids)


def _return_summary_for_no_selection(
    *,
    frame_label: str,
    read_packet: RLoopVesselReadPacketFrame,
    r1: R1GraphGoalFrame,
    budget: RLoopBudgetFrame,
    r2: R2GraphNodeSelectionFrame,
) -> RLoopReturnSummaryFrame:
    frame = RLoopReturnSummaryFrame(
        frame_id=f"R:{frame_label}:vessel_one_step_return_summary_frame",
        r_loop_task_status="partial",
        selected_entry_node_ids=[],
        inspected_graph_node_ids=[],
        final_information_granularity="unknown",
        summary_depth_used=0,
        continuation_status="stop_no_actionable_path",
        budget_status=budget.budget_status,
        source_graph_node_ids=[],
        source_data_ids=[read_packet.packet_id, r1.frame_id, budget.frame_id, r2.frame_id],
        source_trace_ids=_unique_strings([*read_packet.source_trace_ids, *r2.source_trace_ids]),
        generated_by=R_LOOP_VESSEL_ONE_STEP_GENERATOR,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )
    validate_r_loop_return_summary_frame(frame)
    return frame


def _return_summary_for_completed_step(
    *,
    frame_label: str,
    read_packet: RLoopVesselReadPacketFrame,
    r1: R1GraphGoalFrame,
    budget: RLoopBudgetFrame,
    r2: R2GraphNodeSelectionFrame,
    r3: R3GraphInspectionFrame,
    continuation: RLoopContinuationFrame,
) -> RLoopReturnSummaryFrame:
    task_status = "sufficient" if continuation.continuation_status == "stop_sufficient" else "partial"
    if continuation.continuation_status == "stop_failed_final":
        task_status = "failed"
    frame = RLoopReturnSummaryFrame(
        frame_id=f"R:{frame_label}:vessel_one_step_return_summary_frame",
        r_loop_task_status=task_status,
        selected_entry_node_ids=[r2.selected_graph_node_id] if r2.selected_graph_node_id else [],
        inspected_graph_node_ids=[r3.inspected_graph_node_id],
        final_information_granularity=r3.current_information_granularity,
        summary_depth_used=r3.summary_depth,
        continuation_status=continuation.continuation_status,
        budget_status=budget.budget_status,
        source_graph_node_ids=_unique_strings(
            [r2.selected_graph_node_id, r3.inspected_graph_node_id, *r3.child_node_ids]
        ),
        source_data_ids=_unique_strings(
            [
                read_packet.packet_id,
                r1.frame_id,
                budget.frame_id,
                r2.frame_id,
                r3.frame_id,
                continuation.frame_id,
                r2.selected_graph_node_id,
            ]
        ),
        source_trace_ids=_unique_strings(
            [
                *read_packet.source_trace_ids,
                *r1.source_trace_ids,
                *r2.source_trace_ids,
                *r3.source_trace_ids,
                *continuation.source_trace_ids,
            ]
        ),
        generated_by=R_LOOP_VESSEL_ONE_STEP_GENERATOR,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )
    validate_r_loop_return_summary_frame(frame)
    return frame


def _return_summary_for_traverse(
    *,
    frame_label: str,
    read_packet: RLoopVesselReadPacketFrame,
    r1: R1GraphGoalFrame,
    final_budget: RLoopBudgetFrame,
    r2_selections: list[R2GraphNodeSelectionFrame],
    r3_inspections: list[R3GraphInspectionFrame],
    final_continuation: RLoopContinuationFrame | None,
    forced_status: str | None = None,
    forced_continuation_status: str | None = None,
) -> RLoopReturnSummaryFrame:
    selected_ids = _unique_strings(
        [r2.selected_graph_node_id for r2 in r2_selections if r2.selected_graph_node_id]
    )
    inspected_ids = _unique_strings([r3.inspected_graph_node_id for r3 in r3_inspections])
    child_ids = _unique_strings(
        [child_id for r3 in r3_inspections for child_id in r3.child_node_ids]
    )
    continuation_status = forced_continuation_status or (
        final_continuation.continuation_status
        if final_continuation is not None
        else "stop_no_actionable_path"
    )
    task_status = forced_status or (
        "sufficient" if continuation_status == "stop_sufficient" else "partial"
    )
    if continuation_status == "stop_failed_final":
        task_status = "failed"
    final_r3 = r3_inspections[-1] if r3_inspections else None
    frame = RLoopReturnSummaryFrame(
        frame_id=f"R:{frame_label}:vessel_traverse_return_summary_frame",
        r_loop_task_status=task_status,
        selected_entry_node_ids=selected_ids,
        inspected_graph_node_ids=inspected_ids,
        final_information_granularity=(
            final_r3.current_information_granularity if final_r3 is not None else "unknown"
        ),
        summary_depth_used=final_r3.summary_depth if final_r3 is not None else 0,
        continuation_status=continuation_status,
        budget_status=final_budget.budget_status,
        source_graph_node_ids=_unique_strings([*selected_ids, *inspected_ids, *child_ids]),
        source_data_ids=_unique_strings(
            [
                read_packet.packet_id,
                r1.frame_id,
                final_budget.frame_id,
                *[r2.frame_id for r2 in r2_selections],
                *[r3.frame_id for r3 in r3_inspections],
                final_continuation.frame_id if final_continuation is not None else None,
                *selected_ids,
                *inspected_ids,
            ]
        ),
        source_trace_ids=_unique_strings(
            [
                *read_packet.source_trace_ids,
                *r1.source_trace_ids,
                *final_budget.source_trace_ids,
                *[
                    trace_id
                    for r2 in r2_selections
                    for trace_id in r2.source_trace_ids
                ],
                *[
                    trace_id
                    for r3 in r3_inspections
                    for trace_id in r3.source_trace_ids
                ],
                *(
                    final_continuation.source_trace_ids
                    if final_continuation is not None
                    else []
                ),
            ]
        ),
        generated_by=R_LOOP_VESSEL_TRAVERSE_GENERATOR,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )
    validate_r_loop_return_summary_frame(frame)
    return frame


def _record_failure_result(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    frame_id: str,
    created_at: str,
    source_packet_id: str,
    failure_stage: str,
    failure_type: str,
    failure_reason: str,
    source_data_ids: list[str],
    source_trace_ids: list[str],
    llm_call_data_ids: list[str] | None = None,
    r1_goal_frame_id: str | None = None,
    r2_selection_frame_id: str | None = None,
    budget_frame_id: str | None = None,
    selected_graph_node_id: str | None = None,
    output_data_ids: list[str] | None = None,
    failure_payload_summary: dict[str, object] | None = None,
) -> RLoopVesselOneStepRun:
    result_frame = _result_frame(
        frame_id=frame_id,
        created_at=created_at,
        one_step_status="failed",
        failure_stage=failure_stage,
        failure_type=failure_type,
        failure_reason=failure_reason,
        source_packet_id=source_packet_id,
        r1_goal_frame_id=r1_goal_frame_id,
        r2_selection_frame_id=r2_selection_frame_id,
        budget_frame_id=budget_frame_id,
        selected_graph_node_id=selected_graph_node_id,
        llm_call_data_ids=llm_call_data_ids or [],
        output_data_ids=output_data_ids or [],
        source_data_ids=source_data_ids,
        source_trace_ids=source_trace_ids,
        failure_payload_summary=failure_payload_summary,
    )
    trace_event_ids: list[str] = []
    final_output_data_ids = list(output_data_ids or [])
    _record_result_frame(trace_store, data_store, turn_id, result_frame, trace_event_ids, final_output_data_ids)
    return RLoopVesselOneStepRun(
        result_frame=result_frame,
        r1_goal=None,
        budget=None,
        r2_selection=None,
        r3_inspection=None,
        continuation=None,
        return_summary=None,
        trace_event_ids=trace_event_ids,
        output_data_ids=final_output_data_ids,
    )


def _record_traverse_failure_result(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    frame_id: str,
    created_at: str,
    source_packet_id: str,
    failure_stage: str,
    failure_type: str,
    failure_reason: str,
    source_data_ids: list[str],
    source_trace_ids: list[str],
    llm_call_data_ids: list[str] | None = None,
    r1_goal_frame_id: str | None = None,
    output_data_ids: list[str] | None = None,
    failure_payload_summary: dict[str, object] | None = None,
    candidate_layer_surfaces: list[RLoopVesselCandidateLayerSurfaceFrame] | None = None,
    surface_selections: list[RLoopVesselSurfaceSelectionFrame] | None = None,
    r2_selections: list[R2GraphNodeSelectionFrame] | None = None,
    r3_inspections: list[R3GraphInspectionFrame] | None = None,
    graph_surfaces: list[RGraphTraversalCandidateSurfaceFrame] | None = None,
    continuations: list[RLoopContinuationFrame] | None = None,
) -> RLoopVesselTraverseRun:
    result_frame = _traverse_result_frame(
        frame_id=frame_id,
        created_at=created_at,
        traverse_status="failed",
        source_packet_id=source_packet_id,
        failure_stage=failure_stage,
        failure_type=failure_type,
        failure_reason=failure_reason,
        r1_goal_frame_id=r1_goal_frame_id,
        final_budget=None,
        return_summary=None,
        candidate_layer_surfaces=list(candidate_layer_surfaces or []),
        graph_surfaces=list(graph_surfaces or []),
        r2_selections=list(r2_selections or []),
        r3_inspections=list(r3_inspections or []),
        continuations=list(continuations or []),
        llm_call_data_ids=llm_call_data_ids or [],
        output_data_ids=output_data_ids or [],
        source_data_ids=source_data_ids,
        source_trace_ids=source_trace_ids,
        failure_payload_summary=failure_payload_summary,
    )
    trace_event_ids: list[str] = []
    final_output_data_ids = list(output_data_ids or [])
    _record_traverse_result_frame(
        trace_store,
        data_store,
        turn_id,
        result_frame,
        trace_event_ids,
        final_output_data_ids,
    )
    return RLoopVesselTraverseRun(
        result_frame=result_frame,
        r1_goal=None,
        final_budget=None,
        r2_selections=list(r2_selections or []),
        r3_inspections=list(r3_inspections or []),
        continuations=list(continuations or []),
        return_summary=None,
        candidate_layer_surfaces=list(candidate_layer_surfaces or []),
        surface_selections=list(surface_selections or []),
        graph_traversal_candidate_surfaces=list(graph_surfaces or []),
        trace_event_ids=trace_event_ids,
        output_data_ids=final_output_data_ids,
    )


def _result_frame(
    *,
    frame_id: str,
    created_at: str,
    one_step_status: str,
    source_packet_id: str,
    failure_stage: str | None = None,
    failure_type: str | None = None,
    failure_reason: str | None = None,
    r1_goal_frame_id: str | None = None,
    r2_selection_frame_id: str | None = None,
    r3_inspection_frame_id: str | None = None,
    budget_frame_id: str | None = None,
    continuation_frame_id: str | None = None,
    return_summary_frame_id: str | None = None,
    selected_graph_node_id: str | None = None,
    inspected_graph_node_id: str | None = None,
    sufficiency_status: str | None = None,
    continuation_status: str | None = None,
    llm_call_data_ids: list[str] | None = None,
    output_data_ids: list[str] | None = None,
    source_data_ids: list[str] | None = None,
    source_trace_ids: list[str] | None = None,
    failure_payload_summary: dict[str, object] | None = None,
) -> RLoopVesselOneStepResultFrame:
    frame = RLoopVesselOneStepResultFrame(
        frame_id=frame_id,
        created_at=created_at,
        policy_id=R_LOOP_VESSEL_ONE_STEP_POLICY_ID,
        one_step_status=one_step_status,
        failure_stage=failure_stage,
        failure_type=failure_type,
        failure_reason=failure_reason,
        source_packet_id=source_packet_id,
        r1_goal_frame_id=r1_goal_frame_id,
        r2_selection_frame_id=r2_selection_frame_id,
        r3_inspection_frame_id=r3_inspection_frame_id,
        budget_frame_id=budget_frame_id,
        continuation_frame_id=continuation_frame_id,
        return_summary_frame_id=return_summary_frame_id,
        selected_graph_node_id=selected_graph_node_id,
        inspected_graph_node_id=inspected_graph_node_id,
        sufficiency_status=sufficiency_status,
        continuation_status=continuation_status,
        llm_call_data_ids=_unique_strings(llm_call_data_ids or []),
        output_data_ids=_unique_strings(output_data_ids or []),
        source_data_ids=_unique_strings([source_packet_id, *(source_data_ids or [])]),
        source_trace_ids=_unique_strings(source_trace_ids or []),
        failure_payload_summary=failure_payload_summary,
    )
    _validate_result_frame(frame)
    return frame


def _record_result_frame(
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    result_frame: RLoopVesselOneStepResultFrame,
    trace_event_ids: list[str],
    output_data_ids: list[str],
) -> None:
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="R:vessel_one_step",
        event_type="node_output",
        input_ref=result_frame.source_trace_ids,
        output_ref=[result_frame.frame_id],
        schema_status="passed" if result_frame.one_step_status == "completed" else "failed",
    )
    data_store.create_record(
        data_id=result_frame.frame_id,
        data_type=R_LOOP_VESSEL_ONE_STEP_RESULT_DATA_TYPE,
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(result_frame),
    )
    trace_event_ids.append(event.event_id)
    output_data_ids.append(result_frame.frame_id)


def _traverse_result_frame(
    *,
    frame_id: str,
    created_at: str,
    traverse_status: str,
    source_packet_id: str,
    failure_stage: str | None = None,
    failure_type: str | None = None,
    failure_reason: str | None = None,
    r1: R1GraphGoalFrame | None = None,
    r1_goal_frame_id: str | None = None,
    final_budget: RLoopBudgetFrame | None = None,
    return_summary: RLoopReturnSummaryFrame | None = None,
    candidate_layer_surfaces: list[RLoopVesselCandidateLayerSurfaceFrame] | None = None,
    graph_surfaces: list[RGraphTraversalCandidateSurfaceFrame] | None = None,
    r2_selections: list[R2GraphNodeSelectionFrame] | None = None,
    r3_inspections: list[R3GraphInspectionFrame] | None = None,
    continuations: list[RLoopContinuationFrame] | None = None,
    llm_call_data_ids: list[str] | None = None,
    output_data_ids: list[str] | None = None,
    source_data_ids: list[str] | None = None,
    source_trace_ids: list[str] | None = None,
    failure_payload_summary: dict[str, object] | None = None,
    terminal_material_seen_count: int = 0,
    min_terminal_material_count: int = R_TRAVERSE_MIN_TERMINAL_MATERIAL_READS,
    raw_original_material_seen_count: int = 0,
    max_raw_original_material_count: int = R_TRAVERSE_MAX_RAW_ORIGINAL_MATERIAL_READS,
    raw_original_read_cap_reached: bool = False,
    early_stop_guard_trigger_count: int = 0,
) -> RLoopVesselTraverseResultFrame:
    candidate_layer_surfaces = list(candidate_layer_surfaces or [])
    graph_surfaces = list(graph_surfaces or [])
    r2_selections = list(r2_selections or [])
    r3_inspections = list(r3_inspections or [])
    continuations = list(continuations or [])
    selected_ids = _unique_strings(
        [r2.selected_graph_node_id for r2 in r2_selections if r2.selected_graph_node_id]
    )
    inspected_ids = _unique_strings([r3.inspected_graph_node_id for r3 in r3_inspections])
    final_r3 = r3_inspections[-1] if r3_inspections else None
    frame = RLoopVesselTraverseResultFrame(
        frame_id=frame_id,
        created_at=created_at,
        policy_id=R_LOOP_VESSEL_TRAVERSE_POLICY_ID,
        traverse_status=traverse_status,
        failure_stage=failure_stage,
        failure_type=failure_type,
        failure_reason=failure_reason,
        source_packet_id=source_packet_id,
        r1_goal_frame_id=r1.frame_id if r1 is not None else r1_goal_frame_id,
        final_budget_frame_id=final_budget.frame_id if final_budget is not None else None,
        return_summary_frame_id=return_summary.frame_id if return_summary is not None else None,
        step_count=len(r3_inspections),
        selected_graph_node_ids=selected_ids,
        inspected_graph_node_ids=inspected_ids,
        candidate_surface_frame_ids=[surface.frame_id for surface in candidate_layer_surfaces],
        graph_traversal_candidate_surface_frame_ids=[surface.frame_id for surface in graph_surfaces],
        r2_selection_frame_ids=[r2.frame_id for r2 in r2_selections],
        r3_inspection_frame_ids=[r3.frame_id for r3 in r3_inspections],
        continuation_frame_ids=[continuation.frame_id for continuation in continuations],
        final_graph_node_id=final_r3.inspected_graph_node_id if final_r3 is not None else None,
        final_sufficiency_status=final_r3.sufficiency_status if final_r3 is not None else None,
        final_continuation_status=(
            return_summary.continuation_status if return_summary is not None else None
        ),
        r_loop_task_status=return_summary.r_loop_task_status if return_summary is not None else None,
        final_information_granularity=(
            return_summary.final_information_granularity if return_summary is not None else None
        ),
        summary_depth_used=return_summary.summary_depth_used if return_summary is not None else None,
        terminal_material_seen_count=terminal_material_seen_count,
        min_terminal_material_count=min_terminal_material_count,
        raw_original_material_seen_count=raw_original_material_seen_count,
        max_raw_original_material_count=max_raw_original_material_count,
        raw_original_read_cap_reached=raw_original_read_cap_reached,
        early_stop_guard_trigger_count=early_stop_guard_trigger_count,
        llm_call_data_ids=_unique_strings(llm_call_data_ids or []),
        output_data_ids=_unique_strings(output_data_ids or []),
        source_data_ids=_unique_strings(
            [
                source_packet_id,
                *(source_data_ids or []),
                r1.frame_id if r1 is not None else r1_goal_frame_id,
                final_budget.frame_id if final_budget is not None else None,
                return_summary.frame_id if return_summary is not None else None,
                *[surface.frame_id for surface in candidate_layer_surfaces],
                *[surface.frame_id for surface in graph_surfaces],
                *[r2.frame_id for r2 in r2_selections],
                *[r3.frame_id for r3 in r3_inspections],
                *[continuation.frame_id for continuation in continuations],
                *selected_ids,
                *inspected_ids,
            ]
        ),
        source_trace_ids=_unique_strings(source_trace_ids or []),
        failure_payload_summary=failure_payload_summary,
    )
    _validate_traverse_result_frame(frame)
    return frame


def _record_traverse_result_frame(
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    result_frame: RLoopVesselTraverseResultFrame,
    trace_event_ids: list[str],
    output_data_ids: list[str],
) -> None:
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="R:vessel_traverse",
        event_type="node_output",
        input_ref=result_frame.source_trace_ids,
        output_ref=[result_frame.frame_id],
        schema_status="passed" if result_frame.traverse_status == "completed" else "failed",
    )
    data_store.create_record(
        data_id=result_frame.frame_id,
        data_type=R_LOOP_VESSEL_TRAVERSE_RESULT_DATA_TYPE,
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(result_frame),
    )
    trace_event_ids.append(event.event_id)
    output_data_ids.append(result_frame.frame_id)


def _record_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    actor: str,
    data_type: str,
    frame_id: str,
    payload: dict[str, object],
    input_ref: list[str],
    trace_event_ids: list[str],
    output_data_ids: list[str],
) -> None:
    event = trace_store.create_event(
        turn_id=turn_id,
        actor=actor,
        event_type="node_output",
        input_ref=input_ref,
        output_ref=[frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame_id,
        data_type=data_type,
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=payload,
    )
    trace_event_ids.append(event.event_id)
    output_data_ids.append(frame_id)


def _validate_result_frame(frame: RLoopVesselOneStepResultFrame) -> None:
    if frame.generated_by != R_LOOP_VESSEL_ONE_STEP_GENERATOR:
        raise ValueError("RLoopVesselOneStepResultFrame.generated_by must be assembler")
    if frame.info_class != "absolute":
        raise ValueError("RLoopVesselOneStepResultFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("RLoopVesselOneStepResultFrame.semantic_judgement_status must be not_run")
    if frame.one_step_status not in R_LOOP_VESSEL_ONE_STEP_STATUSES:
        raise ValueError("RLoopVesselOneStepResultFrame.one_step_status is invalid")
    if frame.one_step_status == "failed":
        if not frame.failure_stage or not frame.failure_type or not frame.failure_reason:
            raise ValueError("failed RLoopVesselOneStepResultFrame requires failure details")
    if frame.one_step_status == "completed" and frame.failure_stage is not None:
        raise ValueError("completed RLoopVesselOneStepResultFrame must not include failure_stage")


def _validate_traverse_result_frame(frame: RLoopVesselTraverseResultFrame) -> None:
    if frame.generated_by != R_LOOP_VESSEL_TRAVERSE_GENERATOR:
        raise ValueError("RLoopVesselTraverseResultFrame.generated_by must be assembler")
    if frame.info_class != "absolute":
        raise ValueError("RLoopVesselTraverseResultFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("RLoopVesselTraverseResultFrame.semantic status must be not_run")
    if frame.traverse_status not in R_LOOP_VESSEL_TRAVERSE_STATUSES:
        raise ValueError("RLoopVesselTraverseResultFrame.traverse_status is invalid")
    if frame.traverse_status == "failed":
        if not frame.failure_stage or not frame.failure_type or not frame.failure_reason:
            raise ValueError("failed RLoopVesselTraverseResultFrame requires failure details")
    if frame.traverse_status == "completed" and frame.failure_stage is not None:
        raise ValueError("completed RLoopVesselTraverseResultFrame must not include failure_stage")
    if frame.step_count != len(frame.r3_inspection_frame_ids):
        raise ValueError("RLoopVesselTraverseResultFrame.step_count mismatch")
    if len(frame.selected_graph_node_ids) != len(frame.r2_selection_frame_ids):
        raise ValueError("RLoopVesselTraverseResultFrame selected path mismatch")
    for field_name, value in {
        "terminal_material_seen_count": frame.terminal_material_seen_count,
        "min_terminal_material_count": frame.min_terminal_material_count,
        "raw_original_material_seen_count": frame.raw_original_material_seen_count,
        "max_raw_original_material_count": frame.max_raw_original_material_count,
        "early_stop_guard_trigger_count": frame.early_stop_guard_trigger_count,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"RLoopVesselTraverseResultFrame.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"RLoopVesselTraverseResultFrame.{field_name} must not be negative")
    if frame.max_raw_original_material_count < 1:
        raise ValueError("RLoopVesselTraverseResultFrame.max_raw_original_material_count must be positive")
    if frame.raw_original_material_seen_count > frame.max_raw_original_material_count:
        raise ValueError("RLoopVesselTraverseResultFrame raw original count exceeds cap")
    if not isinstance(frame.raw_original_read_cap_reached, bool):
        raise TypeError("RLoopVesselTraverseResultFrame.raw_original_read_cap_reached must be bool")


def _candidate_layer_surface_frame(
    *,
    frame_label: str,
    read_packet: RLoopVesselReadPacketFrame,
    created_at: str,
) -> RLoopVesselCandidateLayerSurfaceFrame:
    surface_records = _candidate_layer_surface_records(read_packet)
    frame = RLoopVesselCandidateLayerSurfaceFrame(
        frame_id=f"R:{frame_label}:vessel_candidate_layer_surface_frame",
        created_at=created_at,
        source_packet_id=read_packet.packet_id,
        surface_count=len(surface_records),
        total_candidate_count=sum(
            int(record.get("candidate_count") or 0)
            for record in surface_records
        ),
        available_surface_ids=[
            str(record["surface_id"])
            for record in surface_records
            if isinstance(record.get("surface_id"), str)
        ],
        surface_records=surface_records,
        source_data_ids=_unique_strings(
            [read_packet.packet_id, *read_packet.source_data_ids]
        ),
        source_trace_ids=list(read_packet.source_trace_ids),
    )
    _validate_candidate_layer_surface_frame(frame)
    return frame


def _candidate_layer_surface_frame_from_graph_surface(
    *,
    frame_label: str,
    read_packet: RLoopVesselReadPacketFrame,
    graph_surface: RGraphTraversalCandidateSurfaceFrame,
    created_at: str,
) -> RLoopVesselCandidateLayerSurfaceFrame:
    surface_records = _candidate_layer_surface_records_from_graph_surface(
        read_packet=read_packet,
        graph_surface=graph_surface,
    )
    frame = RLoopVesselCandidateLayerSurfaceFrame(
        frame_id=f"R:{frame_label}:vessel_candidate_layer_surface_frame",
        created_at=created_at,
        source_packet_id=read_packet.packet_id,
        surface_count=len(surface_records),
        total_candidate_count=sum(
            int(record.get("candidate_count") or 0)
            for record in surface_records
        ),
        available_surface_ids=[
            str(record["surface_id"])
            for record in surface_records
            if isinstance(record.get("surface_id"), str)
        ],
        surface_records=surface_records,
        source_data_ids=_unique_strings(
            [read_packet.packet_id, graph_surface.frame_id, *graph_surface.source_data_ids]
        ),
        source_trace_ids=_unique_strings(
            [*read_packet.source_trace_ids, *graph_surface.source_trace_ids]
        ),
    )
    _validate_candidate_layer_surface_frame(frame)
    return frame


def _candidate_layer_surface_records(
    read_packet: RLoopVesselReadPacketFrame,
) -> list[dict[str, object]]:
    grouped_ids: dict[str, list[str]] = {}
    grouped_meta: dict[str, dict[str, object]] = {}
    first_step_entry_records = _core_ego_first_step_entry_records(read_packet)

    for record in first_step_entry_records:
        graph_node_id = record.get("candidate_node_id")
        if not isinstance(graph_node_id, str) or not graph_node_id:
            continue
        candidate_kind = _surface_text(record.get("candidate_kind"), "entry_bundle")
        data_kind = _surface_text(record.get("data_kind"), candidate_kind)
        surface_id = f"surface:entry:{candidate_kind}:data:{data_kind}"
        grouped_ids.setdefault(surface_id, []).append(graph_node_id)
        grouped_meta.setdefault(
            surface_id,
            {
                "surface_id": surface_id,
                "surface_kind": "entry_candidate_kind",
                "candidate_kind": candidate_kind,
                "data_kind": data_kind,
                "branch_role": _branch_role_for_candidate_kind(candidate_kind),
                "summary_depth": None,
                "info_class": "absolute",
            },
        )

    surface_records: list[dict[str, object]] = []
    for surface_id in _ordered_surface_ids(grouped_meta):
        candidate_ids = _unique_strings(grouped_ids.get(surface_id, []))
        record = dict(grouped_meta[surface_id])
        record["candidate_count"] = len(candidate_ids)
        record["candidate_graph_node_ids"] = candidate_ids
        surface_records.append(record)
    return surface_records


def _candidate_layer_surface_records_from_graph_surface(
    *,
    read_packet: RLoopVesselReadPacketFrame,
    graph_surface: RGraphTraversalCandidateSurfaceFrame,
) -> list[dict[str, object]]:
    records_by_id = _candidate_records_by_id(read_packet)
    grouped_ids: dict[str, list[str]] = {}
    grouped_meta: dict[str, dict[str, object]] = {}
    for graph_node_id in graph_surface.candidate_graph_node_ids:
        if graph_node_id not in records_by_id:
            continue
        record = records_by_id[graph_node_id]
        candidate_kind = _surface_text(record.get("candidate_kind"), "hierarchy_candidate")
        data_kind = _surface_text(record.get("data_kind"), candidate_kind)
        summary_depth = record.get("summary_depth")
        depth_part = str(summary_depth) if isinstance(summary_depth, int) else "unknown"
        surface_id = (
            "surface:hierarchy:"
            f"{_safe_surface_part(candidate_kind)}:"
            f"data:{_safe_surface_part(data_kind)}:"
            f"depth:{depth_part}"
        )
        grouped_ids.setdefault(surface_id, []).append(graph_node_id)
        grouped_meta.setdefault(
            surface_id,
            {
                "surface_id": surface_id,
                "surface_kind": "hierarchy_child_candidate_kind",
                "candidate_kind": candidate_kind,
                "data_kind": data_kind,
                "branch_role": _branch_role_for_record(record),
                "summary_depth": summary_depth if isinstance(summary_depth, int) else None,
                "info_class": _surface_text(record.get("info_class"), "absolute"),
                "current_graph_node_id": graph_surface.inspected_graph_node_id,
            },
        )

    surface_records: list[dict[str, object]] = []
    for surface_id in _ordered_surface_ids(grouped_meta):
        candidate_ids = _unique_strings(grouped_ids.get(surface_id, []))
        record = dict(grouped_meta[surface_id])
        record["candidate_count"] = len(candidate_ids)
        record["candidate_graph_node_ids"] = candidate_ids
        surface_records.append(record)
    return surface_records


def _ordered_surface_ids(
    grouped_meta: dict[str, dict[str, object]],
) -> list[str]:
    return sorted(
        grouped_meta,
        key=lambda surface_id: _surface_sort_key(grouped_meta[surface_id]),
    )


def _surface_sort_key(record: dict[str, object]) -> tuple[int, int, str]:
    surface_id = str(record.get("surface_id") or "")
    candidate_kind = record.get("candidate_kind")
    branch_role = record.get("branch_role")
    depth = record.get("summary_depth")
    if branch_role == "source_material_ingest":
        return (0, 0, surface_id)
    if candidate_kind == "summary" and isinstance(depth, int):
        return (1, -depth, surface_id)
    if branch_role == "conversation_time_memory":
        return (3, 0, surface_id)
    return (2, 0, surface_id)


def _core_ego_first_step_entry_records(
    read_packet: RLoopVesselReadPacketFrame,
) -> list[dict[str, object]]:
    time_axis_records = [
        record
        for record in read_packet.entry_candidate_records
        if record.get("candidate_kind") == "time_axis"
        or record.get("node_kind") == "time_axis"
    ]
    if time_axis_records:
        return time_axis_records
    return list(read_packet.entry_candidate_records)


def _surface_all_candidate_ids(
    candidate_layer_surface: RLoopVesselCandidateLayerSurfaceFrame,
) -> list[str]:
    result: list[str] = []
    for record in candidate_layer_surface.surface_records:
        values = record.get("candidate_graph_node_ids")
        if isinstance(values, list):
            result.extend(item for item in values if isinstance(item, str))
    return _unique_strings(result)


def _surface_current_graph_node_id(
    candidate_layer_surface: RLoopVesselCandidateLayerSurfaceFrame,
) -> str:
    for record in candidate_layer_surface.surface_records:
        value = record.get("current_graph_node_id")
        if isinstance(value, str) and value:
            return value
    return "graph:core_ego:root"


def _candidate_records_by_surface(
    read_packet: RLoopVesselReadPacketFrame,
    candidate_layer_surface: RLoopVesselCandidateLayerSurfaceFrame,
) -> dict[str, list[dict[str, object]]]:
    records_by_id = _candidate_records_by_id(read_packet)
    grouped: dict[str, list[dict[str, object]]] = {}
    for surface_record in candidate_layer_surface.surface_records:
        surface_id = surface_record.get("surface_id")
        if not isinstance(surface_id, str):
            continue
        grouped[surface_id] = []
        for graph_node_id in _surface_candidate_ids(candidate_layer_surface, surface_id):
            candidate_record = records_by_id.get(graph_node_id)
            if candidate_record is not None:
                grouped[surface_id].append(candidate_record)
    return grouped


def _r2_selection_ref_map(
    read_packet: RLoopVesselReadPacketFrame,
    candidate_layer_surface: RLoopVesselCandidateLayerSurfaceFrame,
) -> dict[str, object]:
    candidate_records_by_actual_surface = _candidate_records_by_surface(
        read_packet,
        candidate_layer_surface,
    )
    surface_ref_to_surface_id: dict[str, str] = {}
    node_ref_to_graph_node_id: dict[str, str] = {}
    node_refs_by_surface_ref: dict[str, list[str]] = {}
    surface_records: list[dict[str, object]] = []
    candidate_records_by_surface_ref: dict[str, list[dict[str, object]]] = {}

    node_index = 1
    for surface_index, surface_record in enumerate(candidate_layer_surface.surface_records, start=1):
        surface_id = surface_record.get("surface_id")
        if not isinstance(surface_id, str):
            continue
        surface_ref = f"surface_{surface_index:03d}"
        surface_ref_to_surface_id[surface_ref] = surface_id
        candidate_records_by_surface_ref[surface_ref] = []
        node_refs_by_surface_ref[surface_ref] = []

        candidate_node_refs: list[str] = []
        for candidate_record in candidate_records_by_actual_surface.get(surface_id, []):
            graph_node_id = candidate_record.get("graph_node_id")
            if not isinstance(graph_node_id, str):
                continue
            node_ref = f"node_{node_index:03d}"
            node_index += 1
            node_ref_to_graph_node_id[node_ref] = graph_node_id
            node_refs_by_surface_ref[surface_ref].append(node_ref)
            candidate_node_refs.append(node_ref)
            visible_record = dict(candidate_record)
            visible_record.pop("graph_node_id", None)
            visible_record["node_ref"] = node_ref
            candidate_records_by_surface_ref[surface_ref].append(visible_record)

        surface_records.append(
            {
                "surface_ref": surface_ref,
                "surface_kind": surface_record.get("surface_kind"),
                "candidate_kind": surface_record.get("candidate_kind"),
                "data_kind": surface_record.get("data_kind"),
                "branch_role": surface_record.get("branch_role"),
                "summary_depth": surface_record.get("summary_depth"),
                "info_class": surface_record.get("info_class"),
                "candidate_count": surface_record.get("candidate_count"),
                "candidate_node_refs": candidate_node_refs,
            }
        )

    return {
        "available_surface_refs": list(surface_ref_to_surface_id),
        "surface_records": surface_records,
        "candidate_records_by_surface_ref": candidate_records_by_surface_ref,
        "surface_ref_to_surface_id": surface_ref_to_surface_id,
        "node_ref_to_graph_node_id": node_ref_to_graph_node_id,
        "node_refs_by_surface_ref": node_refs_by_surface_ref,
    }


def _first_visible_ref(payload: dict[str, object]) -> tuple[str | None, str | None, str | None]:
    available_surface_refs = payload.get("available_surface_refs")
    records_by_surface = payload.get("candidate_records_by_surface_ref")
    if not isinstance(available_surface_refs, list) or not isinstance(records_by_surface, dict):
        return None, None, None
    for surface_ref in available_surface_refs:
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


def _r2_selection_ref_map_from_surface(
    candidate_layer_surface: RLoopVesselCandidateLayerSurfaceFrame,
) -> dict[str, object]:
    surface_ref_to_surface_id: dict[str, str] = {}
    node_ref_to_graph_node_id: dict[str, str] = {}
    node_refs_by_surface_ref: dict[str, list[str]] = {}
    node_index = 1
    for surface_index, surface_record in enumerate(candidate_layer_surface.surface_records, start=1):
        surface_id = surface_record.get("surface_id")
        if not isinstance(surface_id, str):
            continue
        surface_ref = f"surface_{surface_index:03d}"
        surface_ref_to_surface_id[surface_ref] = surface_id
        node_refs_by_surface_ref[surface_ref] = []
        values = surface_record.get("candidate_graph_node_ids")
        if isinstance(values, list):
            for graph_node_id in values:
                if not isinstance(graph_node_id, str):
                    continue
                node_ref = f"node_{node_index:03d}"
                node_index += 1
                node_ref_to_graph_node_id[node_ref] = graph_node_id
                node_refs_by_surface_ref[surface_ref].append(node_ref)
    return {
        "available_surface_refs": list(surface_ref_to_surface_id),
        "surface_ref_to_surface_id": surface_ref_to_surface_id,
        "node_ref_to_graph_node_id": node_ref_to_graph_node_id,
        "node_refs_by_surface_ref": node_refs_by_surface_ref,
    }


def _selected_surface_id_from_r2_payload(
    payload: dict[str, object],
    *,
    selection_ref_map: dict[str, object],
) -> str | None:
    selected_surface_ref = payload.get("selected_surface_ref")
    surface_ref_to_surface_id = selection_ref_map.get("surface_ref_to_surface_id")
    if isinstance(selected_surface_ref, str) and isinstance(surface_ref_to_surface_id, dict):
        surface_id = surface_ref_to_surface_id.get(selected_surface_ref)
        return surface_id if isinstance(surface_id, str) else None
    selected_surface_id = payload.get("selected_surface_id")
    return selected_surface_id if isinstance(selected_surface_id, str) else None


def _selected_graph_node_id_from_r2_payload(
    payload: dict[str, object],
    *,
    selection_ref_map: dict[str, object],
) -> str | None:
    selected_node_ref = payload.get("selected_node_ref")
    node_ref_to_graph_node_id = selection_ref_map.get("node_ref_to_graph_node_id")
    if isinstance(selected_node_ref, str) and isinstance(node_ref_to_graph_node_id, dict):
        graph_node_id = node_ref_to_graph_node_id.get(selected_node_ref)
        return graph_node_id if isinstance(graph_node_id, str) else None
    selected_graph_node_id = payload.get("selected_graph_node_id")
    return selected_graph_node_id if isinstance(selected_graph_node_id, str) else None


def _selected_surface_ref_from_r2_payload(payload: dict[str, object]) -> str | None:
    value = payload.get("selected_surface_ref")
    return value if isinstance(value, str) else None


def _selected_node_ref_from_r2_payload(payload: dict[str, object]) -> str | None:
    value = payload.get("selected_node_ref")
    return value if isinstance(value, str) else None


def _candidate_records_by_id(
    read_packet: RLoopVesselReadPacketFrame,
) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for record in read_packet.summary_candidate_records:
        graph_node_id = record.get("summary_node_id")
        if isinstance(graph_node_id, str) and graph_node_id:
            item = _summary_candidate_record_view(record)
            item["graph_node_id"] = graph_node_id
            item["candidate_kind"] = "summary"
            records[graph_node_id] = item
    for record in read_packet.entry_candidate_records:
        graph_node_id = record.get("candidate_node_id")
        if isinstance(graph_node_id, str) and graph_node_id:
            item = _entry_candidate_record_view(record)
            item["graph_node_id"] = graph_node_id
            records[graph_node_id] = item
    return records


def _entry_candidate_record_view(record: dict[str, object]) -> dict[str, object]:
    return {
        "candidate_kind": record.get("candidate_kind"),
        "branch_role": _branch_role_for_record(record),
        "display_name": record.get("display_name"),
        "node_kind": record.get("node_kind"),
        "data_kind": record.get("data_kind"),
        "created_at": record.get("created_at"),
        "written_at": record.get("written_at"),
        "summary_depth": record.get("summary_depth"),
        "source_leaf_count": record.get("source_leaf_count"),
        "source_summary_count": record.get("source_summary_count"),
    }


def _surface_candidate_ids(
    candidate_layer_surface: RLoopVesselCandidateLayerSurfaceFrame,
    surface_id: str | None,
) -> list[str]:
    if not surface_id:
        return []
    for record in candidate_layer_surface.surface_records:
        if record.get("surface_id") == surface_id:
            values = record.get("candidate_graph_node_ids")
            if isinstance(values, list):
                return [item for item in values if isinstance(item, str)]
    return []


def _surface_candidate_ids_for_selection(
    candidate_layer_surface: RLoopVesselCandidateLayerSurfaceFrame,
    selected_surface_id: str | None,
    *,
    fallback_graph_node_ids: list[str],
) -> list[str]:
    selected_surface_ids = _surface_candidate_ids(candidate_layer_surface, selected_surface_id)
    return selected_surface_ids or list(fallback_graph_node_ids)


def _validate_candidate_layer_surface_frame(
    frame: RLoopVesselCandidateLayerSurfaceFrame,
) -> None:
    if frame.generated_by != R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_GENERATOR:
        raise ValueError("RLoopVesselCandidateLayerSurfaceFrame.generated_by is invalid")
    if frame.info_class != "absolute":
        raise ValueError("RLoopVesselCandidateLayerSurfaceFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("RLoopVesselCandidateLayerSurfaceFrame semantic status must be not_run")
    if frame.surface_count != len(frame.surface_records):
        raise ValueError("RLoopVesselCandidateLayerSurfaceFrame.surface_count mismatch")
    surface_ids = [
        record.get("surface_id")
        for record in frame.surface_records
        if isinstance(record.get("surface_id"), str)
    ]
    if frame.available_surface_ids != surface_ids:
        raise ValueError("RLoopVesselCandidateLayerSurfaceFrame.available_surface_ids mismatch")
    for record in frame.surface_records:
        if not isinstance(record.get("candidate_graph_node_ids"), list):
            raise ValueError("candidate layer surface record requires candidate_graph_node_ids")
        if not isinstance(record.get("branch_role"), str) or not record.get("branch_role"):
            raise ValueError("candidate layer surface record requires branch_role")
        if "summary_text" in record:
            raise ValueError("candidate layer surface record must not include summary_text")


def _validate_surface_selection_frame(frame: RLoopVesselSurfaceSelectionFrame) -> None:
    if frame.info_class != "mixed":
        raise ValueError("RLoopVesselSurfaceSelectionFrame.info_class must be mixed")
    if frame.semantic_judgement_status != "ran":
        raise ValueError("RLoopVesselSurfaceSelectionFrame semantic status must be ran")
    if frame.selection_status not in {"selected", "none_selected"}:
        raise ValueError("RLoopVesselSurfaceSelectionFrame.selection_status is invalid")
    if frame.selection_status == "selected":
        if not frame.selected_surface_id:
            raise ValueError("selected RLoopVesselSurfaceSelectionFrame requires selected_surface_id")
        if frame.selected_surface_id not in frame.available_surface_ids:
            raise ValueError("selected_surface_id must be in available_surface_ids")
        if frame.selected_surface_candidate_count < 1:
            raise ValueError("selected surface must contain candidates")
    elif frame.selected_surface_id is not None:
        raise ValueError("none_selected surface selection must not include selected_surface_id")


def _available_graph_node_ids(read_packet: RLoopVesselReadPacketFrame) -> list[str]:
    summary_ids = [
        str(record["summary_node_id"])
        for record in read_packet.summary_candidate_records
        if isinstance(record.get("summary_node_id"), str)
    ]
    entry_ids = [
        str(record["candidate_node_id"])
        for record in read_packet.entry_candidate_records
        if isinstance(record.get("candidate_node_id"), str)
    ]
    return _unique_strings([*summary_ids, *entry_ids])


def _selected_candidate_record(
    read_packet: RLoopVesselReadPacketFrame,
    selected_graph_node_id: str,
) -> dict[str, object]:
    for record in read_packet.summary_candidate_records:
        if record.get("summary_node_id") == selected_graph_node_id:
            return _with_hierarchy_child_candidates(
                read_packet=read_packet,
                selected_record=dict(record),
            )
    for record in read_packet.entry_candidate_records:
        if record.get("candidate_node_id") == selected_graph_node_id:
            return _with_hierarchy_child_candidates(
                read_packet=read_packet,
                selected_record=dict(record),
            )
    raise ValueError("selected graph node id is not present in R Vessel read packet")


def _record_node_id(record: dict[str, object]) -> str:
    value = record.get("summary_node_id") or record.get("candidate_node_id")
    return value if isinstance(value, str) else ""


def _candidate_node_kind(record: dict[str, object]) -> str:
    if record.get("summary_node_id"):
        return "summary"
    value = record.get("node_kind")
    return value if isinstance(value, str) and value else "time_bundle"


def _candidate_summary_depth(record: dict[str, object]) -> int:
    value = record.get("summary_depth")
    return value if isinstance(value, int) and value >= 0 else 0


def _candidate_source_leaf_count(record: dict[str, object]) -> int:
    value = record.get("source_leaf_count")
    return value if isinstance(value, int) and value >= 0 else 0


def _is_terminal_material_record(record: dict[str, object]) -> bool:
    if isinstance(record.get("summary_node_id"), str):
        summary_text = record.get("summary_text")
        if isinstance(summary_text, str) and summary_text.strip():
            return True
        summary_text_char_count = record.get("summary_text_char_count")
        return isinstance(summary_text_char_count, int) and summary_text_char_count > 0

    node_kind = _candidate_node_kind(record)
    candidate_kind = record.get("candidate_kind")
    terminal_kinds = {"raw_source", "raw_capsule"}
    return node_kind in terminal_kinds or candidate_kind in terminal_kinds


def _is_raw_original_material_record(record: dict[str, object]) -> bool:
    node_kind = _candidate_node_kind(record)
    candidate_kind = record.get("candidate_kind")
    return node_kind in {"raw_source", "raw_capsule"} or candidate_kind in {
        "raw_source",
        "raw_capsule",
    }


def _candidate_child_node_ids(record: dict[str, object]) -> list[str]:
    values: list[str | None] = []
    hierarchy_child_node_ids = record.get("hierarchy_child_node_ids")
    if isinstance(hierarchy_child_node_ids, list):
        return _unique_strings(
            [item for item in hierarchy_child_node_ids if isinstance(item, str)]
        )
    source_graph_node_ids = record.get("source_graph_node_ids")
    if isinstance(source_graph_node_ids, list):
        values.extend(item for item in source_graph_node_ids if isinstance(item, str))
    target_graph_node_id = record.get("target_graph_node_id")
    if isinstance(target_graph_node_id, str):
        values.append(target_graph_node_id)
    return _unique_strings(values)


def _with_hierarchy_child_candidates(
    *,
    read_packet: RLoopVesselReadPacketFrame,
    selected_record: dict[str, object],
) -> dict[str, object]:
    selected_node_id = _record_node_id(selected_record)
    child_records = _hierarchy_child_candidate_records(
        read_packet=read_packet,
        selected_node_id=selected_node_id,
        selected_record=selected_record,
    )
    child_node_ids = _unique_strings(
        [
            value
            for record in child_records
            for value in [record.get("candidate_node_id")]
            if isinstance(value, str)
        ]
    )
    result = dict(selected_record)
    result["hierarchy_child_node_ids"] = child_node_ids
    result["hierarchy_child_candidate_records"] = child_records
    return result


def _hierarchy_child_candidate_records(
    *,
    read_packet: RLoopVesselReadPacketFrame,
    selected_node_id: str,
    selected_record: dict[str, object],
) -> list[dict[str, object]]:
    records_by_id = _full_candidate_records_by_id(read_packet)
    summary_child_records = _summary_node_layer_child_records(
        selected_record=selected_record,
        records_by_id=records_by_id,
    )
    if summary_child_records or _summary_node_owns_child_policy(selected_record):
        return summary_child_records

    summary_layer_records = _source_kind_summary_layer_child_records(
        read_packet=read_packet,
        selected_node_id=selected_node_id,
        selected_record=selected_record,
        records_by_id=records_by_id,
    )
    if summary_layer_records:
        return summary_layer_records

    child_ids: list[str] = []

    if _candidate_node_kind(selected_record) == "time_axis":
        child_ids.extend(
            str(record["candidate_node_id"])
            for record in read_packet.entry_candidate_records
            if isinstance(record.get("candidate_node_id"), str)
            and record.get("candidate_node_id") != selected_node_id
            and record.get("candidate_kind")
            in {"time_bundle", "source_ingest_bundle", "source_ingest_time_bundle"}
        )

    source_graph_node_ids = selected_record.get("source_graph_node_ids")
    if isinstance(source_graph_node_ids, list):
        child_ids.extend(item for item in source_graph_node_ids if isinstance(item, str))

    for record in read_packet.entry_candidate_records:
        parent_ids = record.get("parent_graph_node_ids")
        if isinstance(parent_ids, list) and selected_node_id in parent_ids:
            child_id = record.get("candidate_node_id")
            if isinstance(child_id, str):
                child_ids.append(child_id)

    for record in read_packet.summary_candidate_records:
        target_id = record.get("target_graph_node_id")
        if target_id == selected_node_id:
            summary_id = record.get("summary_node_id")
            if isinstance(summary_id, str):
                child_ids.append(summary_id)

    child_records: list[dict[str, object]] = []
    for child_id in _unique_strings(child_ids):
        child_record = records_by_id.get(child_id)
        if child_record is None:
            child_record = {
                "candidate_node_id": child_id,
                "candidate_kind": "unresolved_graph_node",
                "display_name": child_id,
            }
        child_records.append(child_record)
    return child_records


def _summary_node_layer_child_records(
    *,
    selected_record: dict[str, object],
    records_by_id: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    if _candidate_node_kind(selected_record) != "summary":
        return []

    data_kind = selected_record.get("data_kind")
    if data_kind == "token_budget_bundle_summary":
        return _candidate_records_for_ids(
            records_by_id=records_by_id,
            graph_node_ids=_summary_child_summary_ids(selected_record),
        )

    if data_kind == "source_leaf_summary":
        return _candidate_records_for_ids(
            records_by_id=records_by_id,
            graph_node_ids=_summary_child_raw_ids(selected_record),
        )

    return []


def _summary_node_owns_child_policy(record: dict[str, object]) -> bool:
    return _candidate_node_kind(record) == "summary" and record.get("data_kind") in {
        "token_budget_bundle_summary",
        "source_leaf_summary",
    }


def _summary_child_summary_ids(record: dict[str, object]) -> list[str]:
    values: list[str] = []
    for field_name in ("source_graph_node_ids", "source_data_ids"):
        field_value = record.get(field_name)
        if isinstance(field_value, list):
            values.extend(
                item
                for item in field_value
                if isinstance(item, str) and item.startswith("graph:summary:")
            )
    return _unique_strings(values)


def _summary_child_raw_ids(record: dict[str, object]) -> list[str]:
    values: list[str] = []
    for field_name in ("source_graph_node_ids", "source_data_ids"):
        field_value = record.get(field_name)
        if isinstance(field_value, list):
            values.extend(item for item in field_value if _is_raw_source_id(item))
    target_graph_node_id = record.get("target_graph_node_id")
    if _is_raw_source_id(target_graph_node_id):
        values.append(target_graph_node_id)  # type: ignore[arg-type]
    return _unique_strings(values)


def _candidate_records_for_ids(
    *,
    records_by_id: dict[str, dict[str, object]],
    graph_node_ids: list[str],
) -> list[dict[str, object]]:
    return [
        records_by_id[graph_node_id]
        for graph_node_id in graph_node_ids
        if graph_node_id in records_by_id
    ]


def _source_kind_summary_layer_child_records(
    *,
    read_packet: RLoopVesselReadPacketFrame,
    selected_node_id: str,
    selected_record: dict[str, object],
    records_by_id: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    if _candidate_node_kind(selected_record) != "source_kind_bundle":
        return []

    raw_child_ids = _source_kind_raw_child_ids(
        read_packet=read_packet,
        selected_node_id=selected_node_id,
        selected_record=selected_record,
    )
    if not raw_child_ids:
        return []

    token_summary_ids = _summary_ids_covering_any_source(
        read_packet=read_packet,
        source_ids=raw_child_ids,
        data_kind="token_budget_bundle_summary",
    )
    if token_summary_ids:
        return [
            records_by_id[summary_id]
            for summary_id in token_summary_ids
            if summary_id in records_by_id
        ]

    leaf_summary_ids = _summary_ids_covering_any_source(
        read_packet=read_packet,
        source_ids=raw_child_ids,
        data_kind="source_leaf_summary",
    )
    return [
        records_by_id[summary_id]
        for summary_id in leaf_summary_ids
        if summary_id in records_by_id
    ]


def _source_kind_raw_child_ids(
    *,
    read_packet: RLoopVesselReadPacketFrame,
    selected_node_id: str,
    selected_record: dict[str, object],
) -> list[str]:
    child_ids: list[str] = []
    source_graph_node_ids = selected_record.get("source_graph_node_ids")
    if isinstance(source_graph_node_ids, list):
        child_ids.extend(item for item in source_graph_node_ids if _is_raw_source_id(item))

    for record in read_packet.entry_candidate_records:
        parent_ids = record.get("parent_graph_node_ids")
        child_id = record.get("candidate_node_id")
        if (
            isinstance(parent_ids, list)
            and selected_node_id in parent_ids
            and isinstance(child_id, str)
            and _entry_record_is_raw_source(record)
        ):
            child_ids.append(child_id)
    return _unique_strings(child_ids)


def _summary_ids_covering_any_source(
    *,
    read_packet: RLoopVesselReadPacketFrame,
    source_ids: list[str],
    data_kind: str,
) -> list[str]:
    source_id_set = set(source_ids)
    summary_ids: list[str] = []
    for record in read_packet.summary_candidate_records:
        if record.get("data_kind") != data_kind:
            continue
        if not source_id_set.intersection(_summary_record_source_ids(record)):
            continue
        summary_id = record.get("summary_node_id")
        if isinstance(summary_id, str) and summary_id:
            summary_ids.append(summary_id)
    return _unique_strings(summary_ids)


def _summary_record_source_ids(record: dict[str, object]) -> list[str]:
    values: list[str | None] = []
    source_graph_node_ids = record.get("source_graph_node_ids")
    if isinstance(source_graph_node_ids, list):
        values.extend(item for item in source_graph_node_ids if isinstance(item, str))
    source_data_ids = record.get("source_data_ids")
    if isinstance(source_data_ids, list):
        values.extend(item for item in source_data_ids if isinstance(item, str))
    target_graph_node_id = record.get("target_graph_node_id")
    if isinstance(target_graph_node_id, str):
        values.append(target_graph_node_id)
    return _unique_strings(values)


def _entry_record_is_raw_source(record: dict[str, object]) -> bool:
    return (
        record.get("candidate_kind") == "raw_source"
        or record.get("node_kind") == "raw_source"
        or _is_raw_source_id(record.get("candidate_node_id"))
    )


def _branch_role_for_record(record: dict[str, object]) -> str:
    candidate_kind = record.get("candidate_kind")
    if isinstance(candidate_kind, str) and candidate_kind:
        return _branch_role_for_candidate_kind(candidate_kind)

    node_kind = record.get("node_kind")
    if isinstance(node_kind, str) and node_kind:
        return _branch_role_for_candidate_kind(node_kind)

    if isinstance(record.get("summary_node_id"), str):
        return "summary_memory"

    return "unknown_graph_branch"


def _branch_role_for_candidate_kind(candidate_kind: str) -> str:
    if candidate_kind == "time_axis":
        return "graph_axis"
    if candidate_kind in {"source_ingest_bundle", "source_ingest_time_bundle"}:
        return "source_material_ingest"
    if candidate_kind == "source_kind_bundle":
        return "source_material_ingest"
    if candidate_kind in {"raw_source", "token_budget_summary_bundle"}:
        return "source_material_leaf"
    if candidate_kind == "time_bundle":
        return "conversation_time_memory"
    if candidate_kind == "raw_capsule":
        return "conversation_time_memory"
    if candidate_kind == "summary":
        return "summary_memory"
    return "unknown_graph_branch"


def _is_raw_source_id(value: object) -> bool:
    return isinstance(value, str) and value.startswith("graph:raw_source:")


def _full_candidate_records_by_id(
    read_packet: RLoopVesselReadPacketFrame,
) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for record in read_packet.entry_candidate_records:
        graph_node_id = record.get("candidate_node_id")
        if isinstance(graph_node_id, str) and graph_node_id:
            records[graph_node_id] = {
                "candidate_node_id": graph_node_id,
                "candidate_kind": record.get("candidate_kind"),
                "display_name": record.get("display_name"),
                "node_kind": record.get("node_kind"),
                "data_kind": record.get("data_kind"),
                "branch_role": _branch_role_for_record(record),
                "summary_depth": record.get("summary_depth"),
                "source_leaf_count": record.get("source_leaf_count"),
                "source_summary_count": record.get("source_summary_count"),
            }
    for record in read_packet.summary_candidate_records:
        graph_node_id = record.get("summary_node_id")
        if isinstance(graph_node_id, str) and graph_node_id:
            records[graph_node_id] = {
                "candidate_node_id": graph_node_id,
                "candidate_kind": "summary",
                "display_name": record.get("summary_display_name"),
                "node_kind": "summary",
                "data_kind": record.get("data_kind"),
                "branch_role": _branch_role_for_record(record),
                "summary_depth": record.get("summary_depth"),
                "source_leaf_count": record.get("source_leaf_count"),
                "source_summary_count": record.get("source_summary_count"),
                "target_graph_node_id": record.get("target_graph_node_id"),
                "source_graph_node_ids": record.get("source_graph_node_ids"),
                "source_data_ids": record.get("source_data_ids"),
                "summary_text_preview": record.get("summary_text_preview"),
            }
    return records


def _hierarchy_child_candidate_record_views(
    selected_record: dict[str, object],
) -> list[dict[str, object]]:
    records = selected_record.get("hierarchy_child_candidate_records")
    if not isinstance(records, list):
        return []
    result: list[dict[str, object]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        result.append(
            {
                "candidate_kind": record.get("candidate_kind"),
                "display_name": record.get("display_name"),
                "node_kind": record.get("node_kind"),
                "data_kind": record.get("data_kind"),
                "summary_depth": record.get("summary_depth"),
                "source_leaf_count": record.get("source_leaf_count"),
                "source_summary_count": record.get("source_summary_count"),
                "summary_text_preview": record.get("summary_text_preview"),
            }
        )
    return result


def _max_summary_depth(read_packet: RLoopVesselReadPacketFrame) -> int | None:
    depths = [
        record.get("summary_depth")
        for record in read_packet.summary_candidate_records
        if isinstance(record.get("summary_depth"), int)
    ]
    return max(depths) if depths else None


def _payload_text(payload: dict[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    return value.strip() if isinstance(value, str) else ""


def _user_question_anchor_id(user_question: str) -> str:
    digest = hashlib.sha256(user_question.encode("utf-8")).hexdigest()[:16]
    return f"r1_user_question_anchor:{digest}"


def _r1_anchor_id_from_input_payload(input_payload: dict[str, object]) -> str:
    anchor = input_payload.get("user_question_anchor")
    if isinstance(anchor, dict):
        anchor_id = anchor.get("anchor_id")
        if isinstance(anchor_id, str):
            return anchor_id
    return ""


def _surface_text(value: object, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return _safe_surface_part(value)
    return fallback


def _safe_surface_part(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_:-]+", "_", value.strip()) or "unknown"


def _payload_int(payload: dict[str, object], field_name: str) -> int:
    value = payload.get(field_name)
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _shares_user_question_anchor(*, user_question: str, generated_goal: str) -> bool:
    anchors = _question_anchor_tokens(user_question)
    if not anchors:
        return True
    normalized_goal = _normalize_anchor_text(generated_goal)
    return any(anchor in normalized_goal for anchor in anchors)


def _question_anchor_tokens(user_question: str) -> list[str]:
    normalized = _normalize_anchor_text(user_question)
    raw_tokens = re.findall(r"[a-z0-9_]{2,}", normalized)
    blocked = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "how",
        "what",
        "why",
        "one",
        "step",
        "한",
        "단계",
        "골라봐",
        "어떻게",
        "구조",
    }
    anchors: list[str] = []
    for token in raw_tokens:
        if token in blocked:
            continue
        if token in anchors:
            continue
        anchors.append(token)
    return anchors[:8]


def _normalize_anchor_text(text: str) -> str:
    return "".join(
        character.lower() if character.isalnum() or character == "_" else " "
        for character in text
    )


def _prompt(prompt_ref: str) -> str:
    return Path(prompt_ref).read_text(encoding="utf-8")


def _append_llm_refs(result, call_data_ids: list[str], trace_event_ids: list[str]) -> None:
    if result.call_data_id:
        call_data_ids.append(result.call_data_id)
    if result.trace_event_id:
        trace_event_ids.append(result.trace_event_id)


def _safe_frame_label(value: str) -> str:
    normalized = value.strip().replace("-", "_").replace(" ", "_")
    if not normalized:
        return "manual_vessel_r_one_step"
    if not all(ch.isalnum() or ch == "_" for ch in normalized):
        raise ValueError("R Vessel one-step frame_label must contain only letters, numbers, or underscore")
    return normalized


def _result_frame_id(frame_label: str) -> str:
    return f"R:{frame_label}:vessel_one_step_result_frame"


def _traverse_result_frame_id(frame_label: str) -> str:
    return f"R:{frame_label}:vessel_traverse_result_frame"


def _now_from_trace(trace_store: TraceStore) -> str:
    events = trace_store.list_events()
    if events:
        return events[-1].timestamp
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


__all__ = [
    "R1_VESSEL_GOAL_PROMPT_REF",
    "R2_VESSEL_SELECTOR_PROMPT_REF",
    "R3_VESSEL_INSPECTOR_PROMPT_REF",
    "RLoopVesselCandidateLayerSurfaceFrame",
    "RLoopVesselOneStepFakeLLMAdapter",
    "RLoopVesselOneStepResultFrame",
    "RLoopVesselOneStepRun",
    "RLoopVesselSurfaceSelectionFrame",
    "RLoopVesselTraverseFakeLLMAdapter",
    "RLoopVesselTraverseResultFrame",
    "RLoopVesselTraverseRun",
    "R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_DATA_TYPE",
    "R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_GENERATOR",
    "R_LOOP_VESSEL_SURFACE_SELECTION_DATA_TYPE",
    "R_LOOP_VESSEL_ONE_STEP_GENERATOR",
    "R_LOOP_VESSEL_ONE_STEP_POLICY_ID",
    "R_LOOP_VESSEL_ONE_STEP_RESULT_DATA_TYPE",
    "R_LOOP_VESSEL_ONE_STEP_SCHEMA_NAME",
    "R_LOOP_VESSEL_TRAVERSE_GENERATOR",
    "R_LOOP_VESSEL_TRAVERSE_POLICY_ID",
    "R_LOOP_VESSEL_TRAVERSE_RESULT_DATA_TYPE",
    "R_LOOP_VESSEL_TRAVERSE_SCHEMA_NAME",
    "run_r_loop_vessel_one_step",
    "run_r_loop_vessel_traverse",
]
