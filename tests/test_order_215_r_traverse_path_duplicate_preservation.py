from __future__ import annotations

from songryeon_core.core.schemas import (
    R1GraphGoalFrame,
    R2GraphNodeSelectionFrame,
    R3GraphInspectionFrame,
    RLoopBudgetFrame,
)
from songryeon_core.loops.r_loop_vessel_one_step import (
    _return_summary_for_traverse,
    _traverse_result_frame,
)


def test_r_traverse_result_preserves_duplicate_selected_path_entries() -> None:
    r1 = _r1()
    budget = _budget(r1)
    r2_selections = [_r2("R2:1"), _r2("R2:2")]
    r3_inspections = [_r3("R3:1"), _r3("R3:2")]
    return_summary = _return_summary_for_traverse(
        frame_label="order_215",
        read_packet=_packet(),
        r1=r1,
        final_budget=budget,
        r2_selections=r2_selections,
        r3_inspections=r3_inspections,
        final_continuation=None,
        forced_status="partial",
        forced_continuation_status="stop_budget_exhausted",
    )

    frame = _traverse_result_frame(
        frame_id="R:order_215:vessel_traverse_result_frame",
        created_at="2026-07-08T00:00:00",
        traverse_status="completed",
        source_packet_id="packet:order_215",
        r1=r1,
        final_budget=budget,
        return_summary=return_summary,
        r2_selections=r2_selections,
        r3_inspections=r3_inspections,
    )

    assert frame.selected_graph_node_ids == [
        "graph:axis:time",
        "graph:axis:time",
    ]
    assert frame.inspected_graph_node_ids == [
        "graph:axis:time",
        "graph:axis:time",
    ]
    assert len(frame.selected_graph_node_ids) == len(frame.r2_selection_frame_ids)
    assert return_summary.selected_entry_node_ids == ["graph:axis:time"]
    assert return_summary.source_graph_node_ids == ["graph:axis:time"]


def test_r_traverse_result_allows_none_selected_without_path_entry() -> None:
    r1 = _r1()
    budget = _budget(r1)
    r2_selections = [_r2_none_selected()]
    r3_inspections: list[R3GraphInspectionFrame] = []
    return_summary = _return_summary_for_traverse(
        frame_label="order_215_none_selected",
        read_packet=_packet(),
        r1=r1,
        final_budget=budget,
        r2_selections=r2_selections,
        r3_inspections=r3_inspections,
        final_continuation=None,
        forced_status="partial",
        forced_continuation_status="stop_no_actionable_path",
    )

    frame = _traverse_result_frame(
        frame_id="R:order_215_none_selected:vessel_traverse_result_frame",
        created_at="2026-07-08T00:00:00",
        traverse_status="completed",
        source_packet_id="packet:order_215",
        r1=r1,
        final_budget=budget,
        return_summary=return_summary,
        r2_selections=r2_selections,
        r3_inspections=r3_inspections,
    )

    assert frame.r2_selection_frame_ids == ["R2:none_selected"]
    assert frame.selected_graph_node_ids == []
    assert frame.inspected_graph_node_ids == []


def _r1() -> R1GraphGoalFrame:
    return R1GraphGoalFrame(
        frame_id="R1:order_215",
        graph_search_goal="중복 path 보존 테스트",
        required_information_granularity="low_summary",
        allowed_summary_depth=1,
        max_traversal_depth=2,
        max_branch_switches=0,
        max_node_reads=2,
        max_context_tokens=4000,
        stop_condition="테스트 종료",
        source_graph_guide_packet_id="packet:order_215",
        user_question_anchor_id="anchor:order_215",
    )


def _budget(r1: R1GraphGoalFrame) -> RLoopBudgetFrame:
    return RLoopBudgetFrame(
        frame_id="R:order_215:budget",
        source_r1_goal_frame_id=r1.frame_id,
        max_traversal_depth=2,
        max_branch_switches=0,
        max_node_reads=2,
        max_context_tokens=4000,
        used_traversal_depth=2,
        used_node_reads=2,
    )


def _r2(frame_id: str) -> R2GraphNodeSelectionFrame:
    return R2GraphNodeSelectionFrame(
        frame_id=frame_id,
        selection_scope="vessel",
        available_graph_node_ids=["graph:axis:time"],
        selection_status="selected",
        selected_graph_node_id="graph:axis:time",
        selection_reason="반복 path 테스트용 선택",
        expected_information_granularity="low_summary",
        expected_source_kind="axis",
        source_r1_goal_frame_id="R1:order_215",
    )


def _r2_none_selected() -> R2GraphNodeSelectionFrame:
    return R2GraphNodeSelectionFrame(
        frame_id="R2:none_selected",
        selection_scope="vessel",
        available_graph_node_ids=["graph:axis:time"],
        selection_status="none_selected",
        selected_graph_node_id=None,
        selection_reason="테스트용으로 선택 가능한 노드를 고르지 않는다.",
        expected_information_granularity="low_summary",
        expected_source_kind="none",
        source_r1_goal_frame_id="R1:order_215",
    )


def _r3(frame_id: str) -> R3GraphInspectionFrame:
    return R3GraphInspectionFrame(
        frame_id=frame_id,
        inspected_graph_node_id="graph:axis:time",
        node_kind="time_axis",
        child_node_count=1,
        child_node_ids=[],
        summary_depth=0,
        source_leaf_count=0,
        current_information_granularity="low_summary",
        sufficiency_status="insufficient",
        granularity_problem_status="needs_lower_granularity",
        branch_problem_status="none",
        recommended_next_action="deeper",
        inspection_reason="반복 path 테스트용 검사",
        source_r2_selection_frame_id="R2:order_215",
    )


class _packet:
    packet_id = "packet:order_215"
    source_trace_ids: list[str] = []
