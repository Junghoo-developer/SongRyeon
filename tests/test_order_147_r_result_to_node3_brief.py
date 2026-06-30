from __future__ import annotations

import json

from songryeon_core.core.schemas import (
    Node3InputBriefFrame,
    Node3RLoopResultMaterial,
    R_ROUTE_EXPERIMENTAL_NEXT_0_MODE,
)
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.node_2_handoff import node3_brief_llm_payload
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block
from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.terminal_view import render_runtime_view


def test_experimental_r_summary_is_preserved_in_node3_brief() -> None:
    result = run_dry_turn(
        user_input="그래프 기억을 R로 한 번만 실험해줘",
        node_1_router_adapter=RRouteFakeAdapter(),
        enable_r_route_experimental=True,
    )

    brief = _payload(result, "node_3:input_brief_frame")
    material = brief["r_loop_result_material"]

    assert material["source_data_id"] == "R:experimental:return_summary_frame"
    assert material["r_loop_task_status"] == "partial"
    assert material["continuation_status"] == "continue_deeper"
    assert material["budget_status"] == "within_budget"
    assert material["generated_by"] == "CODE:R_ROUTE_EXPERIMENTAL_GATE"
    assert material["info_class"] == "absolute"
    assert material["semantic_judgement_status"] == "not_run"
    assert material["attitude_hint"] == "r_loop_partial_or_skeleton_only"
    assert "R:experimental:return_summary_frame" in brief["source_data_ids"]


def test_node3_grounding_block_marks_r_skeleton_as_limited() -> None:
    frame = _minimal_node3_brief_with_r_material()

    grounding_block = build_node3_grounding_block(frame)

    assert "R 탐색 실험 상태: partial / continue_deeper" in grounding_block
    assert "graph memory 탐색 성공으로 단정하지 않는다" in grounding_block


def test_node3_llm_payload_contains_safe_r_result_boundary() -> None:
    frame = _minimal_node3_brief_with_r_material()

    payload = node3_brief_llm_payload(frame)

    r_loop_result = payload["r_loop_result"]
    assert r_loop_result["status"] == "present"
    assert r_loop_result["task_status"] == "partial"
    assert r_loop_result["attitude_hint"] == "r_loop_partial_or_skeleton_only"
    assert "does not prove" in r_loop_result["boundary"]


def test_terminal_marks_r_result_material_in_node3_brief() -> None:
    result = run_dry_turn(
        user_input="그래프 기억을 R로 한 번만 실험해줘",
        node_1_router_adapter=RRouteFakeAdapter(),
        enable_r_route_experimental=True,
    )

    rendered = render_runtime_view(result, user_input="R experimental")

    assert "R loop result in brief: task=partial" in rendered
    assert "hint=r_loop_partial_or_skeleton_only" in rendered


def _minimal_node3_brief_with_r_material() -> Node3InputBriefFrame:
    return Node3InputBriefFrame(
        frame_id="node_3:input_brief_frame:test",
        turn_id="turn_order_147",
        user_question="R 결과를 설명해줘",
        brief_status="ready",
        handoff_frame_id="node_2:handoff_frame:test",
        r_loop_result_material=Node3RLoopResultMaterial(
            source_data_id="R:experimental:return_summary_frame",
            r_loop_task_status="partial",
            continuation_status="continue_deeper",
            budget_status="within_budget",
            final_information_granularity="summary_depth_0_graph_skeleton",
            summary_depth_used=0,
            selected_entry_node_count=1,
            inspected_graph_node_count=1,
            source_graph_node_count=1,
            generated_by="CODE:R_ROUTE_EXPERIMENTAL_GATE",
            info_class="absolute",
            semantic_judgement_status="not_run",
            attitude_hint="r_loop_partial_or_skeleton_only",
        ),
        source_data_ids=[
            "node_2:handoff_frame:test",
            "R:experimental:return_summary_frame",
        ],
    )


class RRouteFakeAdapter:
    model_id = "r-route-fake"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "node_1 Router" not in request.prompt:
            return LLMResponse(text="{}", model_id=self.model_id, raw={})

        payload = {
            "route": "R",
            "route_reason": "graph memory traversal looks useful",
            "expected_next_0_mode": R_ROUTE_EXPERIMENTAL_NEXT_0_MODE,
            "route_confidence": 0.71,
            "needs_more_memory": False,
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def _payload(result: dict[str, object], data_id: str) -> dict[str, object]:
    for record in result["data_records"]:
        if record["data_id"] == data_id:
            payload = record["payload"]
            if isinstance(payload, dict):
                return payload
    raise AssertionError(f"missing payload: {data_id}")
