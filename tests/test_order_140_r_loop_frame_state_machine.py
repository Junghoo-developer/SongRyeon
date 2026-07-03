from __future__ import annotations

import pytest

from songryeon_core.core.r_loop_state_machine import decide_r_loop_continuation
from songryeon_core.core.schemas import (
    R1GraphGoalFrame,
    R2GraphNodeSelectionFrame,
    R3GraphInspectionFrame,
    RLoopBudgetFrame,
    RLoopReturnSummaryFrame,
    validate_r1_graph_goal_frame,
    validate_r2_graph_node_selection_frame,
    validate_r3_graph_inspection_frame,
    validate_r_loop_return_summary_frame,
)


def test_r2_selection_accepts_only_available_graph_node_id() -> None:
    frame = _r2_selection(selected_graph_node_id="graph:axis:time")

    validate_r2_graph_node_selection_frame(frame)


def test_r2_selection_rejects_node_id_outside_available_list() -> None:
    frame = _r2_selection(selected_graph_node_id="graph:raw_capsule:missing")

    with pytest.raises(ValueError, match="selected_graph_node_id must be available"):
        validate_r2_graph_node_selection_frame(frame)


def test_r3_inspection_preserves_raw_bundle_and_summary_node_kinds() -> None:
    raw = _r3_inspection(
        frame_id="R3:inspect:raw",
        inspected_graph_node_id="graph:raw_capsule:turn_001",
        node_kind="raw_capsule",
        summary_depth=0,
        source_leaf_count=1,
    )
    bundle = _r3_inspection(
        frame_id="R3:inspect:bundle",
        inspected_graph_node_id="graph:time_bundle:batch_001",
        node_kind="time_bundle",
        summary_depth=0,
        source_leaf_count=3,
    )
    summary = _r3_inspection(
        frame_id="R3:inspect:summary",
        inspected_graph_node_id="graph:summary:001",
        node_kind="summary",
        summary_depth=1,
        source_leaf_count=3,
    )

    for frame in (raw, bundle, summary):
        validate_r3_graph_inspection_frame(frame)

    assert raw.node_kind == "raw_capsule"
    assert bundle.node_kind == "time_bundle"
    assert summary.node_kind == "summary"
    assert summary.summary_depth == 1


def test_continuation_distinguishes_deeper_from_branch_switch() -> None:
    budget = _budget()
    deeper = decide_r_loop_continuation(
        frame_id="R:continuation:deeper",
        r3_inspection=_r3_inspection(
            recommended_next_action="deeper",
            granularity_problem_status="needs_lower_granularity",
            child_node_ids=["graph:raw_capsule:turn_001"],
        ),
        budget=budget,
    )
    switch = decide_r_loop_continuation(
        frame_id="R:continuation:switch",
        r3_inspection=_r3_inspection(
            recommended_next_action="switch_branch",
            granularity_problem_status="none",
            branch_problem_status="wrong_branch",
            child_node_ids=[],
        ),
        budget=budget,
    )

    assert deeper.continuation_status == "continue_deeper"
    assert deeper.next_target_node == "R2"
    assert deeper.continuation_reason_code == "CODE_STATUS:r3_needs_lower_granularity"
    assert switch.continuation_status == "continue_switch_branch"
    assert switch.next_target_node == "R2"
    assert switch.continuation_reason_code == "CODE_STATUS:r3_recommends_branch_switch"


def test_continuation_closes_when_budget_is_exhausted() -> None:
    continuation = decide_r_loop_continuation(
        frame_id="R:continuation:budget",
        r3_inspection=_r3_inspection(
            recommended_next_action="deeper",
            granularity_problem_status="needs_lower_granularity",
            child_node_ids=["graph:raw_capsule:turn_001"],
        ),
        budget=_budget(used_node_reads=3),
    )

    assert continuation.continuation_status == "stop_budget_exhausted"
    assert continuation.next_target_node == "return_summary"
    assert continuation.remaining_node_reads == 0


def test_schema_only_frames_keep_llm_semantic_judgement_not_run() -> None:
    r1 = R1GraphGoalFrame(
        frame_id="R1:goal",
        graph_search_goal="schema-only graph goal placeholder",
        required_information_granularity="unknown",
        allowed_summary_depth=0,
        max_traversal_depth=2,
        max_branch_switches=1,
        max_node_reads=3,
        max_context_tokens=1200,
        stop_condition="schema_only_stop_condition",
        source_graph_guide_packet_id="rloop:graph_guide:graph:snapshot:turn_001",
        source_data_ids=["rloop:graph_guide:graph:snapshot:turn_001"],
    )
    r2 = _r2_selection(selected_graph_node_id="graph:axis:time")
    r3 = _r3_inspection()
    budget = _budget()
    continuation = decide_r_loop_continuation(
        frame_id="R:continuation:not_run",
        r3_inspection=r3,
        budget=budget,
    )
    summary = RLoopReturnSummaryFrame(
        frame_id="R:return_summary",
        r_loop_task_status="not_run",
        selected_entry_node_ids=["graph:axis:time"],
        inspected_graph_node_ids=[r3.inspected_graph_node_id],
        final_information_granularity="unknown",
        summary_depth_used=0,
        continuation_status=continuation.continuation_status,
        budget_status=budget.budget_status,
        source_graph_node_ids=["graph:axis:time"],
        source_data_ids=[r1.frame_id, r2.frame_id, r3.frame_id, continuation.frame_id],
    )

    validate_r1_graph_goal_frame(r1)
    validate_r2_graph_node_selection_frame(r2)
    validate_r3_graph_inspection_frame(r3)
    validate_r_loop_return_summary_frame(summary)

    assert r1.semantic_judgement_status == "not_run"
    assert r2.semantic_judgement_status == "not_run"
    assert r3.semantic_judgement_status == "not_run"
    assert continuation.semantic_judgement_status == "not_run"
    assert summary.semantic_judgement_status == "not_run"


def _r2_selection(*, selected_graph_node_id: str | None) -> R2GraphNodeSelectionFrame:
    return R2GraphNodeSelectionFrame(
        frame_id="R2:selection",
        selection_scope="core_ego_time_axis",
        available_graph_node_ids=["graph:axis:time", "graph:time_bundle:turn_001"],
        selection_status="selected",
        selected_graph_node_id=selected_graph_node_id,
        selection_reason="",
        expected_information_granularity="unknown",
        expected_source_kind="time_axis",
        source_r1_goal_frame_id="R1:goal",
        source_data_ids=["R1:goal"],
    )


def _r3_inspection(
    *,
    frame_id: str = "R3:inspection",
    inspected_graph_node_id: str = "graph:time_bundle:turn_001",
    node_kind: str = "time_bundle",
    summary_depth: int = 0,
    source_leaf_count: int = 1,
    recommended_next_action: str = "deeper",
    granularity_problem_status: str = "needs_lower_granularity",
    branch_problem_status: str = "none",
    child_node_ids: list[str] | None = None,
) -> R3GraphInspectionFrame:
    children = ["graph:raw_capsule:turn_001"] if child_node_ids is None else child_node_ids
    return R3GraphInspectionFrame(
        frame_id=frame_id,
        inspected_graph_node_id=inspected_graph_node_id,
        node_kind=node_kind,
        child_node_count=len(children),
        child_node_ids=children,
        summary_depth=summary_depth,
        source_leaf_count=source_leaf_count,
        current_information_granularity="medium_summary",
        sufficiency_status="insufficient",
        granularity_problem_status=granularity_problem_status,
        branch_problem_status=branch_problem_status,
        recommended_next_action=recommended_next_action,
        inspection_reason="",
        source_r2_selection_frame_id="R2:selection",
        source_data_ids=["R2:selection"],
    )


def _budget(*, used_node_reads: int = 1) -> RLoopBudgetFrame:
    return RLoopBudgetFrame(
        frame_id="R:budget",
        source_r1_goal_frame_id="R1:goal",
        max_traversal_depth=2,
        max_branch_switches=1,
        max_node_reads=3,
        max_context_tokens=1200,
        used_traversal_depth=1,
        used_branch_switches=0,
        used_node_reads=used_node_reads,
        used_context_tokens=200,
        source_data_ids=["R1:goal"],
    )
