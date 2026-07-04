from __future__ import annotations

from songryeon_core.llm.fake import SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.loops.r_loop_vessel_one_step import RLoopVesselTraverseFakeLLMAdapter
from songryeon_core.runtime.dry_run import run_dry_turn

from tests.test_order_175_vessel_backed_r_read_packet import (
    FailingDriverFactory,
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


def test_default_turn_does_not_run_vessel_r_without_gate() -> None:
    result = _run_live_vessel_turn(enable_vessel_r_route=False)

    assert result["vessel_r_route_enabled"] is False
    assert result["vessel_r_route_status"] == "not_run"
    assert result["vessel_r_read_packet_status"] == "not_run"
    assert result["vessel_r_return_packet_status"] == "not_run"
    assert result["node3_vessel_r_material_status"] in {
        "none",
        "not_present",
        "not_recorded",
    }


def test_vessel_r_gate_runs_live_r_and_returns_material_to_node3() -> None:
    result = _run_live_vessel_turn(enable_vessel_r_route=True)

    assert result["vessel_r_route_enabled"] is True
    assert result["vessel_r_route_status"] == "selected"
    assert result["vessel_r_read_packet_status"] == "passed"
    assert result["vessel_r_traverse_status"] == "completed"
    assert result["vessel_r_task_status"] == "sufficient"
    assert result["vessel_r_return_packet_status"] == "available"
    assert result["vessel_r_node3_material_ready"] is True
    assert result["vessel_r_close_route_id"] == "route:2"
    assert "R:Vessel_R1_R2_R3_traverse" in result["route2_handoff_path"]
    assert result["node3_brief_status"] == "ready"
    assert result["node3_vessel_r_material_status"] == "present"
    assert result["node3_vessel_r_material_count"] == 4
    assert result["turn_activity_graph_link_r_vessel_ledger_count"] == 1
    assert result["node4_gate_status"] == "pass"
    assert "Vessel R" in str(result["report"])
    assert "문서 읽기 도구 근거가 아니라" in str(result["report"])


def test_vessel_r_read_failure_still_closes_to_node2_safely() -> None:
    result = _run_live_vessel_turn(
        enable_vessel_r_route=True,
        driver_factory=FailingDriverFactory(),
    )

    assert result["vessel_r_route_status"] == "selected"
    assert result["vessel_r_read_packet_status"] == "read_failed"
    assert result["vessel_r_traverse_status"] == "failed"
    assert result["vessel_r_return_packet_status"] == "failed"
    assert result["vessel_r_node3_material_ready"] is False
    assert result["vessel_r_close_route_id"] == "route:2"
    assert result["node3_vessel_r_material_status"] == "failed"
    assert result["node4_gate_status"] == "pass"
    assert "완료 상태로 단정하지 않고" in str(result["report"])


def _run_live_vessel_turn(
    *,
    enable_vessel_r_route: bool,
    driver_factory: object | None = None,
) -> dict[str, object]:
    adapter = SongRyeonAllNodesFakeLLMAdapter()
    return run_dry_turn(
        user_input="Vessel 그래프 기억 구조를 설명해줘",
        turn_id="turn_order_200_live",
        node_1_router_adapter=adapter,
        memory_relevance_selector_adapter=adapter,
        l1_goal_adapter=adapter,
        l_tool_scope_adapter=adapter,
        l2_query_planner_adapter=adapter,
        l3_result_adapter=adapter,
        node_2_boundary_adapter=adapter,
        node_3_reporter_adapter=adapter,
        node_4_gatekeeper_adapter=adapter,
        enable_vessel_r_route=enable_vessel_r_route,
        vessel_r_adapter=(
            RLoopVesselTraverseFakeLLMAdapter() if enable_vessel_r_route else None
        ),
        vessel_r_allow_no_auth=True,
        vessel_r_driver_factory_for_test=driver_factory
        or FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
                _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
            ],
            summary_rows=[_summary_row()],
        ),
    )
