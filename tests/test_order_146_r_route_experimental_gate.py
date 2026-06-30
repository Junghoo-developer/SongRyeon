from __future__ import annotations

import json

import pytest

from songryeon_core.core.schemas import (
    R_ROUTE_EXPERIMENTAL_NEXT_0_MODE,
    R_ROUTE_EXPERIMENTAL_POLICY_FLAG,
    RoutingDecisionFrame,
    validate_routing_decision_frame,
)
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.node_1_router import _validate_llm_routing_payload
from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.terminal_view import render_runtime_view


def test_route_r_llm_payload_is_rejected_without_explicit_experimental_gate() -> None:
    payload = {
        "route": "R",
        "route_reason": "graph memory traversal looks useful",
        "expected_next_0_mode": R_ROUTE_EXPERIMENTAL_NEXT_0_MODE,
    }

    with pytest.raises(ValueError, match="node_1 route must be L or 2"):
        _validate_llm_routing_payload(payload)


def test_route_r_llm_payload_is_accepted_with_explicit_experimental_gate() -> None:
    payload = {
        "route": "R",
        "route_reason": "graph memory traversal looks useful",
        "expected_next_0_mode": R_ROUTE_EXPERIMENTAL_NEXT_0_MODE,
    }

    _validate_llm_routing_payload(payload, allow_r_route_experimental=True)


def test_route_r_frame_requires_policy_flag_llm_source_and_r_handoff_mode() -> None:
    frame = RoutingDecisionFrame(
        frame_id="route:R",
        turn_id="turn_order_146",
        route="R",
        route_reason="graph memory traversal looks useful",
        expected_next_0_mode=R_ROUTE_EXPERIMENTAL_NEXT_0_MODE,
        route_source="LLM:r-route-fake",
        llm_routing_status="ran",
        route_rule_id="llm_router",
        policy_flag=R_ROUTE_EXPERIMENTAL_POLICY_FLAG,
    )
    validate_routing_decision_frame(frame)

    missing_policy = RoutingDecisionFrame(
        frame_id="route:R",
        turn_id="turn_order_146",
        route="R",
        route_reason="graph memory traversal looks useful",
        expected_next_0_mode=R_ROUTE_EXPERIMENTAL_NEXT_0_MODE,
        route_source="LLM:r-route-fake",
        llm_routing_status="ran",
        route_rule_id="llm_router",
    )
    with pytest.raises(ValueError, match="experimental policy flag"):
        validate_routing_decision_frame(missing_policy)


def test_experimental_r_route_runs_skeleton_then_closes_to_route_2() -> None:
    result = run_dry_turn(
        user_input="그래프 기억을 R로 한 번만 실험해줘",
        node_1_router_adapter=RRouteFakeAdapter(),
        enable_r_route_experimental=True,
    )

    assert result["current_route"] == "2"
    assert result["r_route_experimental_enabled"] is True
    assert result["r_route_experimental_status"] == "selected"
    assert result["r_route_experimental_handoff_packet_id"] == (
        "node_0:r_loop_memory_handoff_packet_frame:r_route_experimental"
    )
    assert result["r_route_experimental_return_summary_id"] == (
        "R:experimental:return_summary_frame"
    )
    assert result["r_route_experimental_close_route_id"] == "route:2"
    assert len(result["r_route_experimental_output_data_ids"]) == 6
    assert "route:R" in result["data_ids"]
    assert "route:2" in result["data_ids"]

    route_r = _payload(result, "route:R")
    assert route_r["policy_flag"] == R_ROUTE_EXPERIMENTAL_POLICY_FLAG
    assert route_r["route_source"] == "LLM:r-route-fake"
    assert route_r["expected_next_0_mode"] == R_ROUTE_EXPERIMENTAL_NEXT_0_MODE

    summary = _payload(result, "R:experimental:return_summary_frame")
    assert summary["generated_by"] == "CODE:R_ROUTE_EXPERIMENTAL_GATE"
    assert summary["info_class"] == "absolute"
    assert summary["semantic_judgement_status"] == "not_run"


def test_experimental_r_route_is_not_available_without_gate() -> None:
    result = run_dry_turn(
        user_input="그래프 기억을 R로 한 번만 실험해줘",
        node_1_router_adapter=RRouteFakeAdapter(),
        enable_r_route_experimental=False,
    )

    assert result["current_route"] in {"2", "L"}
    assert result["r_route_experimental_enabled"] is False
    assert result["r_route_experimental_status"] == "not_run"
    assert "route:R" not in result["data_ids"]


def test_terminal_marks_experimental_r_separately_from_dry_run() -> None:
    result = run_dry_turn(
        user_input="그래프 기억을 R로 한 번만 실험해줘",
        node_1_router_adapter=RRouteFakeAdapter(),
        enable_r_route_experimental=True,
    )

    rendered = render_runtime_view(result, user_input="R experimental")

    assert "- R experimental route skeleton [CODE:R_ROUTE_EXPERIMENTAL_GATE]:" in rendered
    assert "- R dry-run skeleton [CODE:R_LOOP_DRY_RUN_ONLY]:" not in rendered


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
