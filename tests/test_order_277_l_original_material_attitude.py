from __future__ import annotations

from songryeon_core.core.schemas import Node3InputBriefFrame
from songryeon_core.nodes.node_2_handoff import _l_loop_result_attitude_hint
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block


def test_semantic_failure_without_original_material_uses_no_original_hint() -> None:
    hint = _l_loop_result_attitude_hint(
        {
            "l_loop_task_status": "partial",
            "failure_level": "budget_exhausted",
            "l3_goal_match_status": "partial",
            "l3_semantic_goal_match_status": "not_run",
            "l3_semantic_execution_status": "failed",
            "original_material_count": 0,
            "evidence_acquisition_status": "candidates_only",
        }
    )

    assert hint == "l_loop_no_original_material_l3_semantic_failed"


def test_semantic_failure_with_original_material_keeps_acquired_hint() -> None:
    hint = _l_loop_result_attitude_hint(
        {
            "l_loop_task_status": "partial",
            "failure_level": "l3_semantic_failed",
            "l3_goal_match_status": "matched",
            "l3_semantic_goal_match_status": "not_run",
            "l3_semantic_execution_status": "failed",
            "original_material_count": 1,
            "evidence_acquisition_status": "original_material_acquired",
        }
    )

    assert hint == "l_loop_original_material_acquired_l3_semantic_failed"


def test_grounding_block_does_not_call_candidate_context_original_material() -> None:
    brief = Node3InputBriefFrame(
        frame_id="node_3:input_brief_frame",
        turn_id="turn_order_277",
        user_question="후보 수와 실제 원문 수를 구분해줘",
        brief_status="ready",
        handoff_frame_id="node_2:handoff_frame",
        actual_tool_read_doc_count=0,
        supplied_document_context_count=1,
        final_search_candidate_count=12,
        accumulated_search_candidate_count=12,
        l_loop_task_status="partial",
        l_loop_failure_level="budget_exhausted",
        l3_goal_match_status="partial",
        l3_semantic_goal_match_status="not_run",
        l3_semantic_execution_status="failed",
        l3_semantic_failure_type="schema_failed",
        l3_semantic_failure_reason="L3 semantic evidence material_ref was not supplied",
        l_evidence_acquisition_status="candidates_only",
        l_original_material_count=0,
        l_original_material_requirement_status="not_required",
        l_loop_result_attitude_hint=(
            "l_loop_no_original_material_l3_semantic_failed"
        ),
        source_trace_ids=["trace_order_277"],
        source_data_ids=["node_2:handoff_frame", "L:return_summary_frame"],
    )

    grounding = build_node3_grounding_block(brief)

    assert "실제 read_doc 도구 원문 읽기: 0개" in grounding
    assert "node_3 공급 문서 context: 1개" in grounding
    assert "실제 L 원문을 확보하지 못했고" in grounding
    assert "검색 후보와 처리 장부를 원문 근거처럼 말하지 않는다" in grounding
    assert "L 원문은 확보됐지만" not in grounding
