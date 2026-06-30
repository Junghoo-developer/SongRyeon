from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.schemas import (
    R3GraphInspectionFrame,
    RLoopBudgetFrame,
    RLoopContinuationFrame,
    validate_r3_graph_inspection_frame,
    validate_r_loop_budget_frame,
    validate_r_loop_continuation_frame,
)


def decide_r_loop_continuation(
    *,
    frame_id: str,
    r3_inspection: R3GraphInspectionFrame,
    budget: RLoopBudgetFrame,
    source_trace_ids: list[str] | None = None,
) -> RLoopContinuationFrame:
    """Decide R-loop continuation from structured R3 status and numeric budgets only."""

    if not frame_id:
        raise ValueError("frame_id must not be empty")
    validate_r3_graph_inspection_frame(r3_inspection)
    validate_r_loop_budget_frame(budget)

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

    continuation_status, reason_code, next_target_node = _decide_status(
        r3_inspection=r3_inspection,
        remaining_traversal_depth=remaining_traversal_depth,
        remaining_branch_switches=remaining_branch_switches,
        remaining_node_reads=remaining_node_reads,
        remaining_context_tokens=remaining_context_tokens,
    )

    frame = RLoopContinuationFrame(
        frame_id=frame_id,
        source_r3_inspection_frame_id=r3_inspection.frame_id,
        source_budget_frame_id=budget.frame_id,
        continuation_status=continuation_status,
        continuation_reason_code=reason_code,
        next_target_node=next_target_node,
        remaining_traversal_depth=remaining_traversal_depth,
        remaining_branch_switches=remaining_branch_switches,
        remaining_node_reads=remaining_node_reads,
        remaining_context_tokens=remaining_context_tokens,
        source_data_ids=[
            r3_inspection.frame_id,
            budget.frame_id,
            *r3_inspection.source_data_ids,
            *budget.source_data_ids,
        ],
        source_trace_ids=_unique_strings(
            [
                *(source_trace_ids or []),
                *r3_inspection.source_trace_ids,
                *budget.source_trace_ids,
            ]
        ),
    )
    frame.source_data_ids = _unique_strings(frame.source_data_ids)
    validate_r_loop_continuation_frame(frame)
    return frame


def r_loop_continuation_payload(frame: RLoopContinuationFrame) -> dict[str, object]:
    validate_r_loop_continuation_frame(frame)
    return asdict(frame)


def _decide_status(
    *,
    r3_inspection: R3GraphInspectionFrame,
    remaining_traversal_depth: int,
    remaining_branch_switches: int,
    remaining_node_reads: int,
    remaining_context_tokens: int,
) -> tuple[str, str, str]:
    if (
        r3_inspection.sufficiency_status == "sufficient"
        or r3_inspection.recommended_next_action == "stop"
    ):
        return "stop_sufficient", "CODE_STATUS:r3_sufficient", "return_summary"

    if remaining_node_reads <= 0 or remaining_context_tokens <= 0:
        return (
            "stop_budget_exhausted",
            "CODE_STATUS:r_loop_node_or_context_budget_exhausted",
            "return_summary",
        )

    wants_deeper = (
        r3_inspection.recommended_next_action == "deeper"
        or r3_inspection.granularity_problem_status == "needs_lower_granularity"
    )
    if wants_deeper:
        if r3_inspection.child_node_count <= 0:
            return (
                "stop_no_actionable_path",
                "CODE_STATUS:r_loop_no_child_node_for_deeper_traversal",
                "return_summary",
            )
        if remaining_traversal_depth <= 0:
            return (
                "stop_budget_exhausted",
                "CODE_STATUS:r_loop_traversal_depth_budget_exhausted",
                "return_summary",
            )
        return (
            "continue_deeper",
            "CODE_STATUS:r3_needs_lower_granularity",
            "R2",
        )

    wants_branch_switch = (
        r3_inspection.recommended_next_action == "switch_branch"
        or r3_inspection.branch_problem_status == "wrong_branch"
    )
    if wants_branch_switch:
        if remaining_branch_switches <= 0:
            return (
                "stop_budget_exhausted",
                "CODE_STATUS:r_loop_branch_switch_budget_exhausted",
                "return_summary",
            )
        return (
            "continue_switch_branch",
            "CODE_STATUS:r3_recommends_branch_switch",
            "R2",
        )

    if r3_inspection.recommended_next_action == "fail":
        return "stop_failed_final", "CODE_STATUS:r3_failed_final", "return_summary"

    return (
        "stop_no_actionable_path",
        "CODE_STATUS:r_loop_no_actionable_path",
        "return_summary",
    )


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
