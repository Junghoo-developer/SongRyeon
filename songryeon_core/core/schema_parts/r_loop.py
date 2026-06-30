from __future__ import annotations

from dataclasses import dataclass, field

from songryeon_core.core.schema_parts.base import (
    _validate_no_duplicates,
    _validate_string_list,
)
from songryeon_core.core.schema_parts.graph_memory import GRAPH_MEMORY_NODE_KINDS


R1_GRAPH_GOAL_FRAME_SCHEMA_NAME = "R1GraphGoalFrame"
R1_GRAPH_GOAL_FRAME_SCHEMA_VERSION = "0.1"
R_LOOP_BUDGET_FRAME_SCHEMA_NAME = "RLoopBudgetFrame"
R_LOOP_BUDGET_FRAME_SCHEMA_VERSION = "0.1"
R2_GRAPH_NODE_SELECTION_FRAME_SCHEMA_NAME = "R2GraphNodeSelectionFrame"
R2_GRAPH_NODE_SELECTION_FRAME_SCHEMA_VERSION = "0.1"
R3_GRAPH_INSPECTION_FRAME_SCHEMA_NAME = "R3GraphInspectionFrame"
R3_GRAPH_INSPECTION_FRAME_SCHEMA_VERSION = "0.1"
R_LOOP_CONTINUATION_FRAME_SCHEMA_NAME = "RLoopContinuationFrame"
R_LOOP_CONTINUATION_FRAME_SCHEMA_VERSION = "0.1"
R_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_NAME = "RLoopReturnSummaryFrame"
R_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_VERSION = "0.1"

R_LOOP_SCHEMA_ONLY_GENERATOR = "CODE:R_LOOP_SCHEMA_ONLY"

R_INFORMATION_GRANULARITIES = {
    "raw",
    "low_summary",
    "medium_summary",
    "high_summary",
    "unknown",
}
R_SELECTION_STATUSES = {"selected", "none_selected", "failed"}
R_SUFFICIENCY_STATUSES = {"sufficient", "insufficient", "unknown"}
R_GRANULARITY_PROBLEM_STATUSES = {"none", "needs_lower_granularity", "unknown"}
R_BRANCH_PROBLEM_STATUSES = {"none", "wrong_branch", "unknown"}
R_RECOMMENDED_NEXT_ACTIONS = {"stop", "deeper", "switch_branch", "fail"}
R_LOOP_CONTINUATION_STATUSES = {
    "stop_sufficient",
    "continue_deeper",
    "continue_switch_branch",
    "stop_budget_exhausted",
    "stop_no_actionable_path",
    "stop_failed_final",
}
R_LOOP_NEXT_TARGETS = {"R2", "return_summary"}
R_LOOP_TASK_STATUSES = {"not_run", "sufficient", "partial", "failed"}
R_LOOP_INFO_CLASSES = {"relative", "mixed"}
R_LOOP_SEMANTIC_STATUSES = {"not_run", "ran", "failed"}


@dataclass
class R1GraphGoalFrame:
    frame_id: str
    graph_search_goal: str
    required_information_granularity: str
    allowed_summary_depth: int
    max_traversal_depth: int
    max_branch_switches: int
    max_node_reads: int
    max_context_tokens: int
    stop_condition: str
    source_graph_guide_packet_id: str
    source_data_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    generated_by: str = R_LOOP_SCHEMA_ONLY_GENERATOR
    info_class: str = "mixed"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R1_GRAPH_GOAL_FRAME_SCHEMA_NAME
    schema_version: str = R1_GRAPH_GOAL_FRAME_SCHEMA_VERSION


@dataclass
class RLoopBudgetFrame:
    frame_id: str
    source_r1_goal_frame_id: str
    max_traversal_depth: int
    max_branch_switches: int
    max_node_reads: int
    max_context_tokens: int
    used_traversal_depth: int = 0
    used_branch_switches: int = 0
    used_node_reads: int = 0
    used_context_tokens: int = 0
    budget_status: str = "within_budget"
    source_data_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    generated_by: str = R_LOOP_SCHEMA_ONLY_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R_LOOP_BUDGET_FRAME_SCHEMA_NAME
    schema_version: str = R_LOOP_BUDGET_FRAME_SCHEMA_VERSION


@dataclass
class R2GraphNodeSelectionFrame:
    frame_id: str
    selection_scope: str
    available_graph_node_ids: list[str]
    selection_status: str
    selected_graph_node_id: str | None
    selection_reason: str
    expected_information_granularity: str
    expected_source_kind: str
    source_r1_goal_frame_id: str
    source_data_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    generated_by: str = R_LOOP_SCHEMA_ONLY_GENERATOR
    info_class: str = "mixed"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R2_GRAPH_NODE_SELECTION_FRAME_SCHEMA_NAME
    schema_version: str = R2_GRAPH_NODE_SELECTION_FRAME_SCHEMA_VERSION


@dataclass
class R3GraphInspectionFrame:
    frame_id: str
    inspected_graph_node_id: str
    node_kind: str
    child_node_count: int
    child_node_ids: list[str]
    summary_depth: int
    source_leaf_count: int
    current_information_granularity: str
    sufficiency_status: str
    granularity_problem_status: str
    branch_problem_status: str
    recommended_next_action: str
    inspection_reason: str
    source_r2_selection_frame_id: str
    source_data_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    generated_by: str = R_LOOP_SCHEMA_ONLY_GENERATOR
    info_class: str = "mixed"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R3_GRAPH_INSPECTION_FRAME_SCHEMA_NAME
    schema_version: str = R3_GRAPH_INSPECTION_FRAME_SCHEMA_VERSION


@dataclass
class RLoopContinuationFrame:
    frame_id: str
    source_r3_inspection_frame_id: str
    source_budget_frame_id: str
    continuation_status: str
    continuation_reason_code: str
    next_target_node: str
    remaining_traversal_depth: int
    remaining_branch_switches: int
    remaining_node_reads: int
    remaining_context_tokens: int
    source_data_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    generated_by: str = R_LOOP_SCHEMA_ONLY_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R_LOOP_CONTINUATION_FRAME_SCHEMA_NAME
    schema_version: str = R_LOOP_CONTINUATION_FRAME_SCHEMA_VERSION


@dataclass
class RLoopReturnSummaryFrame:
    frame_id: str
    r_loop_task_status: str
    selected_entry_node_ids: list[str]
    inspected_graph_node_ids: list[str]
    final_information_granularity: str
    summary_depth_used: int
    continuation_status: str
    budget_status: str
    source_graph_node_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    generated_by: str = R_LOOP_SCHEMA_ONLY_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_NAME
    schema_version: str = R_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_VERSION


def validate_r1_graph_goal_frame(frame: R1GraphGoalFrame) -> None:
    _require_text_fields(
        "R1GraphGoalFrame",
        {
            "frame_id": frame.frame_id,
            "graph_search_goal": frame.graph_search_goal,
            "required_information_granularity": frame.required_information_granularity,
            "stop_condition": frame.stop_condition,
            "source_graph_guide_packet_id": frame.source_graph_guide_packet_id,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    _validate_schema(frame.schema_name, R1_GRAPH_GOAL_FRAME_SCHEMA_NAME, "R1GraphGoalFrame")
    _validate_schema_version(
        frame.schema_version,
        R1_GRAPH_GOAL_FRAME_SCHEMA_VERSION,
        "R1GraphGoalFrame",
    )
    _validate_granularity("R1GraphGoalFrame.required_information_granularity", frame.required_information_granularity)
    _validate_loop_semantic_fields(
        info_class=frame.info_class,
        semantic_judgement_status=frame.semantic_judgement_status,
        class_name="R1GraphGoalFrame",
    )
    _validate_non_negative_ints(
        "R1GraphGoalFrame",
        {
            "allowed_summary_depth": frame.allowed_summary_depth,
            "max_traversal_depth": frame.max_traversal_depth,
            "max_branch_switches": frame.max_branch_switches,
            "max_node_reads": frame.max_node_reads,
            "max_context_tokens": frame.max_context_tokens,
        },
    )
    _validate_string_list("R1GraphGoalFrame.source_data_ids", frame.source_data_ids)
    _validate_string_list("R1GraphGoalFrame.source_trace_ids", frame.source_trace_ids)
    _validate_no_duplicates("R1GraphGoalFrame.source_data_ids", frame.source_data_ids)
    _validate_no_duplicates("R1GraphGoalFrame.source_trace_ids", frame.source_trace_ids)
    if frame.source_graph_guide_packet_id not in frame.source_data_ids:
        raise ValueError("R1GraphGoalFrame.source_data_ids must include source_graph_guide_packet_id")


def validate_r_loop_budget_frame(frame: RLoopBudgetFrame) -> None:
    _require_text_fields(
        "RLoopBudgetFrame",
        {
            "frame_id": frame.frame_id,
            "source_r1_goal_frame_id": frame.source_r1_goal_frame_id,
            "budget_status": frame.budget_status,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    _validate_schema(frame.schema_name, R_LOOP_BUDGET_FRAME_SCHEMA_NAME, "RLoopBudgetFrame")
    _validate_schema_version(
        frame.schema_version,
        R_LOOP_BUDGET_FRAME_SCHEMA_VERSION,
        "RLoopBudgetFrame",
    )
    if frame.info_class != "absolute":
        raise ValueError("RLoopBudgetFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("RLoopBudgetFrame.semantic_judgement_status must be not_run")
    _validate_non_negative_ints(
        "RLoopBudgetFrame",
        {
            "max_traversal_depth": frame.max_traversal_depth,
            "max_branch_switches": frame.max_branch_switches,
            "max_node_reads": frame.max_node_reads,
            "max_context_tokens": frame.max_context_tokens,
            "used_traversal_depth": frame.used_traversal_depth,
            "used_branch_switches": frame.used_branch_switches,
            "used_node_reads": frame.used_node_reads,
            "used_context_tokens": frame.used_context_tokens,
        },
    )
    if frame.used_traversal_depth > frame.max_traversal_depth:
        raise ValueError("RLoopBudgetFrame.used_traversal_depth must not exceed max")
    if frame.used_branch_switches > frame.max_branch_switches:
        raise ValueError("RLoopBudgetFrame.used_branch_switches must not exceed max")
    if frame.used_node_reads > frame.max_node_reads:
        raise ValueError("RLoopBudgetFrame.used_node_reads must not exceed max")
    if frame.used_context_tokens > frame.max_context_tokens:
        raise ValueError("RLoopBudgetFrame.used_context_tokens must not exceed max")
    _validate_string_list("RLoopBudgetFrame.source_data_ids", frame.source_data_ids)
    _validate_string_list("RLoopBudgetFrame.source_trace_ids", frame.source_trace_ids)
    _validate_no_duplicates("RLoopBudgetFrame.source_data_ids", frame.source_data_ids)
    _validate_no_duplicates("RLoopBudgetFrame.source_trace_ids", frame.source_trace_ids)
    if frame.source_r1_goal_frame_id not in frame.source_data_ids:
        raise ValueError("RLoopBudgetFrame.source_data_ids must include source_r1_goal_frame_id")


def validate_r2_graph_node_selection_frame(frame: R2GraphNodeSelectionFrame) -> None:
    _require_text_fields(
        "R2GraphNodeSelectionFrame",
        {
            "frame_id": frame.frame_id,
            "selection_scope": frame.selection_scope,
            "selection_status": frame.selection_status,
            "expected_information_granularity": frame.expected_information_granularity,
            "expected_source_kind": frame.expected_source_kind,
            "source_r1_goal_frame_id": frame.source_r1_goal_frame_id,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    _validate_schema(
        frame.schema_name,
        R2_GRAPH_NODE_SELECTION_FRAME_SCHEMA_NAME,
        "R2GraphNodeSelectionFrame",
    )
    _validate_schema_version(
        frame.schema_version,
        R2_GRAPH_NODE_SELECTION_FRAME_SCHEMA_VERSION,
        "R2GraphNodeSelectionFrame",
    )
    _validate_member("R2GraphNodeSelectionFrame.selection_status", frame.selection_status, R_SELECTION_STATUSES)
    _validate_granularity("R2GraphNodeSelectionFrame.expected_information_granularity", frame.expected_information_granularity)
    _validate_loop_semantic_fields(
        info_class=frame.info_class,
        semantic_judgement_status=frame.semantic_judgement_status,
        class_name="R2GraphNodeSelectionFrame",
    )
    _validate_string_list(
        "R2GraphNodeSelectionFrame.available_graph_node_ids",
        frame.available_graph_node_ids,
    )
    _validate_string_list("R2GraphNodeSelectionFrame.source_data_ids", frame.source_data_ids)
    _validate_string_list("R2GraphNodeSelectionFrame.source_trace_ids", frame.source_trace_ids)
    _validate_no_duplicates(
        "R2GraphNodeSelectionFrame.available_graph_node_ids",
        frame.available_graph_node_ids,
    )
    _validate_no_duplicates("R2GraphNodeSelectionFrame.source_data_ids", frame.source_data_ids)
    _validate_no_duplicates("R2GraphNodeSelectionFrame.source_trace_ids", frame.source_trace_ids)
    if frame.source_r1_goal_frame_id not in frame.source_data_ids:
        raise ValueError("R2GraphNodeSelectionFrame.source_data_ids must include source_r1_goal_frame_id")
    if frame.selection_status == "selected":
        if not frame.selected_graph_node_id:
            raise ValueError("selected R2GraphNodeSelectionFrame must include selected_graph_node_id")
        if frame.selected_graph_node_id not in frame.available_graph_node_ids:
            raise ValueError("R2GraphNodeSelectionFrame.selected_graph_node_id must be available")
    elif frame.selected_graph_node_id is not None:
        raise ValueError("non-selected R2GraphNodeSelectionFrame must not include selected_graph_node_id")


def validate_r3_graph_inspection_frame(frame: R3GraphInspectionFrame) -> None:
    _require_text_fields(
        "R3GraphInspectionFrame",
        {
            "frame_id": frame.frame_id,
            "inspected_graph_node_id": frame.inspected_graph_node_id,
            "node_kind": frame.node_kind,
            "current_information_granularity": frame.current_information_granularity,
            "sufficiency_status": frame.sufficiency_status,
            "granularity_problem_status": frame.granularity_problem_status,
            "branch_problem_status": frame.branch_problem_status,
            "recommended_next_action": frame.recommended_next_action,
            "source_r2_selection_frame_id": frame.source_r2_selection_frame_id,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    _validate_schema(frame.schema_name, R3_GRAPH_INSPECTION_FRAME_SCHEMA_NAME, "R3GraphInspectionFrame")
    _validate_schema_version(
        frame.schema_version,
        R3_GRAPH_INSPECTION_FRAME_SCHEMA_VERSION,
        "R3GraphInspectionFrame",
    )
    _validate_member("R3GraphInspectionFrame.node_kind", frame.node_kind, GRAPH_MEMORY_NODE_KINDS)
    _validate_granularity("R3GraphInspectionFrame.current_information_granularity", frame.current_information_granularity)
    _validate_member("R3GraphInspectionFrame.sufficiency_status", frame.sufficiency_status, R_SUFFICIENCY_STATUSES)
    _validate_member(
        "R3GraphInspectionFrame.granularity_problem_status",
        frame.granularity_problem_status,
        R_GRANULARITY_PROBLEM_STATUSES,
    )
    _validate_member(
        "R3GraphInspectionFrame.branch_problem_status",
        frame.branch_problem_status,
        R_BRANCH_PROBLEM_STATUSES,
    )
    _validate_member(
        "R3GraphInspectionFrame.recommended_next_action",
        frame.recommended_next_action,
        R_RECOMMENDED_NEXT_ACTIONS,
    )
    _validate_loop_semantic_fields(
        info_class=frame.info_class,
        semantic_judgement_status=frame.semantic_judgement_status,
        class_name="R3GraphInspectionFrame",
    )
    _validate_non_negative_ints(
        "R3GraphInspectionFrame",
        {
            "child_node_count": frame.child_node_count,
            "summary_depth": frame.summary_depth,
            "source_leaf_count": frame.source_leaf_count,
        },
    )
    if frame.child_node_count != len(frame.child_node_ids):
        raise ValueError("R3GraphInspectionFrame.child_node_count must mirror child_node_ids length")
    _validate_string_list("R3GraphInspectionFrame.child_node_ids", frame.child_node_ids)
    _validate_string_list("R3GraphInspectionFrame.source_data_ids", frame.source_data_ids)
    _validate_string_list("R3GraphInspectionFrame.source_trace_ids", frame.source_trace_ids)
    _validate_no_duplicates("R3GraphInspectionFrame.child_node_ids", frame.child_node_ids)
    _validate_no_duplicates("R3GraphInspectionFrame.source_data_ids", frame.source_data_ids)
    _validate_no_duplicates("R3GraphInspectionFrame.source_trace_ids", frame.source_trace_ids)
    if frame.source_r2_selection_frame_id not in frame.source_data_ids:
        raise ValueError("R3GraphInspectionFrame.source_data_ids must include source_r2_selection_frame_id")


def validate_r_loop_continuation_frame(frame: RLoopContinuationFrame) -> None:
    _require_text_fields(
        "RLoopContinuationFrame",
        {
            "frame_id": frame.frame_id,
            "source_r3_inspection_frame_id": frame.source_r3_inspection_frame_id,
            "source_budget_frame_id": frame.source_budget_frame_id,
            "continuation_status": frame.continuation_status,
            "continuation_reason_code": frame.continuation_reason_code,
            "next_target_node": frame.next_target_node,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    _validate_schema(frame.schema_name, R_LOOP_CONTINUATION_FRAME_SCHEMA_NAME, "RLoopContinuationFrame")
    _validate_schema_version(
        frame.schema_version,
        R_LOOP_CONTINUATION_FRAME_SCHEMA_VERSION,
        "RLoopContinuationFrame",
    )
    _validate_member(
        "RLoopContinuationFrame.continuation_status",
        frame.continuation_status,
        R_LOOP_CONTINUATION_STATUSES,
    )
    _validate_member("RLoopContinuationFrame.next_target_node", frame.next_target_node, R_LOOP_NEXT_TARGETS)
    if frame.info_class != "absolute":
        raise ValueError("RLoopContinuationFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("RLoopContinuationFrame.semantic_judgement_status must be not_run")
    _validate_non_negative_ints(
        "RLoopContinuationFrame",
        {
            "remaining_traversal_depth": frame.remaining_traversal_depth,
            "remaining_branch_switches": frame.remaining_branch_switches,
            "remaining_node_reads": frame.remaining_node_reads,
            "remaining_context_tokens": frame.remaining_context_tokens,
        },
    )
    _validate_string_list("RLoopContinuationFrame.source_data_ids", frame.source_data_ids)
    _validate_string_list("RLoopContinuationFrame.source_trace_ids", frame.source_trace_ids)
    _validate_no_duplicates("RLoopContinuationFrame.source_data_ids", frame.source_data_ids)
    _validate_no_duplicates("RLoopContinuationFrame.source_trace_ids", frame.source_trace_ids)
    if frame.source_r3_inspection_frame_id not in frame.source_data_ids:
        raise ValueError("RLoopContinuationFrame.source_data_ids must include R3 frame")
    if frame.source_budget_frame_id not in frame.source_data_ids:
        raise ValueError("RLoopContinuationFrame.source_data_ids must include budget frame")


def validate_r_loop_return_summary_frame(frame: RLoopReturnSummaryFrame) -> None:
    _require_text_fields(
        "RLoopReturnSummaryFrame",
        {
            "frame_id": frame.frame_id,
            "r_loop_task_status": frame.r_loop_task_status,
            "final_information_granularity": frame.final_information_granularity,
            "continuation_status": frame.continuation_status,
            "budget_status": frame.budget_status,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    _validate_schema(
        frame.schema_name,
        R_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_NAME,
        "RLoopReturnSummaryFrame",
    )
    _validate_schema_version(
        frame.schema_version,
        R_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_VERSION,
        "RLoopReturnSummaryFrame",
    )
    _validate_member("RLoopReturnSummaryFrame.r_loop_task_status", frame.r_loop_task_status, R_LOOP_TASK_STATUSES)
    _validate_granularity("RLoopReturnSummaryFrame.final_information_granularity", frame.final_information_granularity)
    _validate_member(
        "RLoopReturnSummaryFrame.continuation_status",
        frame.continuation_status,
        R_LOOP_CONTINUATION_STATUSES,
    )
    if frame.info_class != "absolute":
        raise ValueError("RLoopReturnSummaryFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("RLoopReturnSummaryFrame.semantic_judgement_status must be not_run")
    _validate_non_negative_ints(
        "RLoopReturnSummaryFrame",
        {"summary_depth_used": frame.summary_depth_used},
    )
    _validate_string_list("RLoopReturnSummaryFrame.selected_entry_node_ids", frame.selected_entry_node_ids)
    _validate_string_list("RLoopReturnSummaryFrame.inspected_graph_node_ids", frame.inspected_graph_node_ids)
    _validate_string_list("RLoopReturnSummaryFrame.source_graph_node_ids", frame.source_graph_node_ids)
    _validate_string_list("RLoopReturnSummaryFrame.source_data_ids", frame.source_data_ids)
    _validate_string_list("RLoopReturnSummaryFrame.source_trace_ids", frame.source_trace_ids)
    _validate_no_duplicates(
        "RLoopReturnSummaryFrame.selected_entry_node_ids",
        frame.selected_entry_node_ids,
    )
    _validate_no_duplicates(
        "RLoopReturnSummaryFrame.inspected_graph_node_ids",
        frame.inspected_graph_node_ids,
    )
    _validate_no_duplicates("RLoopReturnSummaryFrame.source_graph_node_ids", frame.source_graph_node_ids)
    _validate_no_duplicates("RLoopReturnSummaryFrame.source_data_ids", frame.source_data_ids)
    _validate_no_duplicates("RLoopReturnSummaryFrame.source_trace_ids", frame.source_trace_ids)


def _validate_loop_semantic_fields(
    *,
    info_class: str,
    semantic_judgement_status: str,
    class_name: str,
) -> None:
    if info_class not in R_LOOP_INFO_CLASSES:
        raise ValueError(f"{class_name}.info_class must be relative or mixed")
    if semantic_judgement_status not in R_LOOP_SEMANTIC_STATUSES:
        raise ValueError(f"unknown {class_name}.semantic_judgement_status: {semantic_judgement_status}")


def _validate_granularity(field_name: str, value: str) -> None:
    _validate_member(field_name, value, R_INFORMATION_GRANULARITIES)


def _validate_schema(value: str, expected: str, class_name: str) -> None:
    if value != expected:
        raise ValueError(f"unknown {class_name} schema_name: {value}")


def _validate_schema_version(value: str, expected: str, class_name: str) -> None:
    if value != expected:
        raise ValueError(f"unknown {class_name} schema_version: {value}")


def _validate_member(field_name: str, value: str, allowed_values: set[str]) -> None:
    if value not in allowed_values:
        raise ValueError(f"unknown {field_name}: {value}")


def _validate_non_negative_ints(class_name: str, values: dict[str, int]) -> None:
    for field_name, value in values.items():
        if not isinstance(value, int):
            raise TypeError(f"{class_name}.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"{class_name}.{field_name} must not be negative")


def _require_text_fields(class_name: str, values: dict[str, str]) -> None:
    for field_name, value in values.items():
        if not isinstance(value, str) or not value:
            raise ValueError(f"{class_name}.{field_name} must not be empty")


__all__ = [
    "R1GraphGoalFrame",
    "R2GraphNodeSelectionFrame",
    "R3GraphInspectionFrame",
    "RLoopBudgetFrame",
    "RLoopContinuationFrame",
    "RLoopReturnSummaryFrame",
    "R1_GRAPH_GOAL_FRAME_SCHEMA_NAME",
    "R1_GRAPH_GOAL_FRAME_SCHEMA_VERSION",
    "R2_GRAPH_NODE_SELECTION_FRAME_SCHEMA_NAME",
    "R2_GRAPH_NODE_SELECTION_FRAME_SCHEMA_VERSION",
    "R3_GRAPH_INSPECTION_FRAME_SCHEMA_NAME",
    "R3_GRAPH_INSPECTION_FRAME_SCHEMA_VERSION",
    "R_LOOP_BUDGET_FRAME_SCHEMA_NAME",
    "R_LOOP_BUDGET_FRAME_SCHEMA_VERSION",
    "R_LOOP_CONTINUATION_FRAME_SCHEMA_NAME",
    "R_LOOP_CONTINUATION_FRAME_SCHEMA_VERSION",
    "R_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_NAME",
    "R_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_VERSION",
    "R_LOOP_CONTINUATION_STATUSES",
    "R_LOOP_SCHEMA_ONLY_GENERATOR",
    "validate_r1_graph_goal_frame",
    "validate_r2_graph_node_selection_frame",
    "validate_r3_graph_inspection_frame",
    "validate_r_loop_budget_frame",
    "validate_r_loop_continuation_frame",
    "validate_r_loop_return_summary_frame",
]
