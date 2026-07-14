from __future__ import annotations

import copy
import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.llm.fake import SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.loops.r_loop_vessel_one_step import (
    RLoopVesselTraverseFakeLLMAdapter,
)
from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.same_turn_r_reroute import (
    SameTurnRReroutePolicy,
    run_same_turn_r_reroute_controller,
)
from songryeon_core.runtime.terminal_view import render_runtime_view

from tests.test_order_175_vessel_backed_r_read_packet import (
    FakeRLoopVesselDriverFactory,
)
from tests.test_order_184_r_vessel_multi_step_traversal import (
    SOURCE_KIND_ID,
    SUMMARY_ID,
    _source_ingest_row,
    _source_kind_row,
    _summary_row,
    _time_axis_row,
)


class RThenRThenTwoAdapter:
    """node_1만 R -> R -> 2로 고정하고 나머지 노드는 기존 fake에 맡긴다."""

    model_id = "order-254-r-r-2-fake"

    def __init__(self) -> None:
        self.delegate = SongRyeonAllNodesFakeLLMAdapter()
        self.node1_allowed_routes: list[list[str]] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "node_1 Router" not in request.prompt:
            return self.delegate.complete(request)

        allowed_routes = request.input_payload.get("allowed_routes")
        normalized_routes = (
            [item for item in allowed_routes if isinstance(item, str)]
            if isinstance(allowed_routes, list)
            else []
        )
        self.node1_allowed_routes.append(normalized_routes)
        route_context = str(request.input_payload.get("route_context") or "entry")
        if route_context == "entry" or "R" in normalized_routes:
            route = "R"
            next_mode = "vessel_r_read_packet"
        else:
            route = "2"
            next_mode = "final_trace_for_2"
        payload = {
            "route": route,
            "route_reason": f"ORDER_254 deterministic {route_context} route",
            "expected_next_0_mode": next_mode,
            "route_confidence": 0.9,
            "needs_more_memory": False,
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class CapturingRTraverseAdapter:
    model_id = "order-254-capturing-r-traverse-fake"

    def __init__(self) -> None:
        self.delegate = RLoopVesselTraverseFakeLLMAdapter()
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(copy.deepcopy(request))
        return self.delegate.complete(request)


def test_same_turn_r_policy_is_closed_by_default_and_ceiling_is_two() -> None:
    assert SameTurnRReroutePolicy().enabled is False
    assert SameTurnRReroutePolicy().effective_max_r_runs_per_turn == 2
    assert SameTurnRReroutePolicy(max_r_runs_per_turn=99).effective_max_r_runs_per_turn == 2
    assert SameTurnRReroutePolicy(max_r_runs_per_turn=99).v0_ceiling_applied is True


def test_same_turn_r_controller_does_not_replace_node1_l_decision() -> None:
    trace_store = TraceStore()
    data_store = DataStore()

    _, _, frame = run_same_turn_r_reroute_controller(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_254_controller_l",
        current_run_index=1,
        policy=SameTurnRReroutePolicy(enabled=True),
        node1_route="L",
        node1_route_data_id="R:run:0001:return:route:L",
        run_memory_frame_id="R:run:0001:node_0:return_memory_frame",
        source_trace_ids=[],
        source_data_ids=[],
    )

    assert frame.controller_decision == "continue_L"
    assert frame.planned_next_route == "L"
    assert frame.same_turn_rerun_allowed is False


def test_policy_enabled_node1_r_return_runs_vessel_r_twice_and_then_closes() -> None:
    node_adapter = RThenRThenTwoAdapter()
    r_adapter = CapturingRTraverseAdapter()

    result = run_dry_turn(
        user_input="Vessel 그래프 기억을 두 단계로 다시 살펴봐",
        turn_id="turn_order_254_two_r_runs",
        node_1_router_adapter=node_adapter,
        memory_relevance_selector_adapter=node_adapter,
        l1_goal_adapter=node_adapter,
        l_tool_scope_adapter=node_adapter,
        l2_query_planner_adapter=node_adapter,
        l3_result_adapter=node_adapter,
        node_2_boundary_adapter=node_adapter,
        node_3_reporter_adapter=node_adapter,
        node_4_gatekeeper_adapter=node_adapter,
        enable_vessel_r_route=True,
        same_turn_r_reroute_enabled=True,
        max_r_runs_per_turn=99,
        vessel_r_adapter=r_adapter,
        vessel_r_allow_no_auth=True,
        vessel_r_driver_factory_for_test=_driver_factory(),
    )

    assert result["vessel_r_run_count"] == 2
    assert result["effective_max_r_runs_per_turn"] == 2
    assert result["vessel_r_run_frame_ids"] == [
        "R:run:0001:run_frame",
        "R:run:0002:run_frame",
    ]
    assert result["vessel_r_top_level_memory_frame_ids"] == [
        "R:run:0001:node_0:return_memory_frame",
        "R:run:0002:node_0:return_memory_frame",
    ]
    assert result["r_reroute_controller_data_ids"] == [
        "R:run:0001:reroute_controller_frame",
        "R:run:0002:reroute_controller_frame",
    ]
    assert result["vessel_r_close_route_id"] == "R:run:0002:return:route:2"
    assert result["same_turn_r_rerun_allowed"] is False
    assert result["turn_activity_graph_link_r_vessel_ledger_count"] == 2

    first_controller = _payload(
        result,
        "R:run:0001:reroute_controller_frame",
    )
    second_controller = _payload(
        result,
        "R:run:0002:reroute_controller_frame",
    )
    assert first_controller["controller_decision"] == "rerun_R"
    assert first_controller["same_turn_rerun_allowed"] is True
    assert second_controller["controller_decision"] == "close_route_2"
    assert second_controller["same_turn_rerun_allowed"] is False

    second_memory = _payload(
        result,
        "R:run:0002:node_0:return_memory_frame",
    )
    assert (
        second_memory["prior_run_memory_frame_id"]
        == "R:run:0001:node_0:return_memory_frame"
    )

    # 첫 진입에는 R이 있고, 1회차 복귀에도 R이 있지만, 2회차 뒤에는 R이 사라진다.
    assert node_adapter.node1_allowed_routes == [
        ["L", "2", "R"],
        ["L", "2", "R"],
        ["L", "2"],
    ]
    prior_memory_requests = [
        request
        for request in r_adapter.requests
        if "prior_top_level_r_run_memory" in request.input_payload
    ]
    assert prior_memory_requests
    assert any(
        _has_prior_seen_candidate(request.input_payload)
        for request in prior_memory_requests
        if "official_selection_table" in request.input_payload
    )
    rendered = render_runtime_view(result, user_input="ORDER_254 runtime")
    assert "actual_r_runs=2" in rendered
    assert "decision=rerun_R" in rendered


def _driver_factory() -> FakeRLoopVesselDriverFactory:
    return FakeRLoopVesselDriverFactory(
        entry_rows=[
            _time_axis_row(),
            _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
            _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
        ],
        summary_rows=[_summary_row()],
    )


def _payload(result: dict[str, object], data_id: str) -> dict[str, object]:
    records = result.get("data_records")
    assert isinstance(records, list)
    for record in records:
        if not isinstance(record, dict) or record.get("data_id") != data_id:
            continue
        payload = record.get("payload")
        assert isinstance(payload, dict)
        return payload
    raise AssertionError(f"missing data payload: {data_id}")


def _has_prior_seen_candidate(payload: dict[str, object]) -> bool:
    table = payload.get("official_selection_table")
    if not isinstance(table, dict):
        return False
    candidate_rows = table.get("candidate_rows")
    if not isinstance(candidate_rows, list):
        return False
    return any(
        isinstance(record, dict) and record.get("seen_in_prior_top_level_r_run") is True
        for record in candidate_rows
    )
