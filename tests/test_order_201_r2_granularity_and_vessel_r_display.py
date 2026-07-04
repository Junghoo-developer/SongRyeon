from __future__ import annotations

from songryeon_core.core.schemas import R1GraphGoalFrame
from songryeon_core.loops.r_loop_vessel_one_step import (
    R_INFORMATION_GRANULARITY_ENUM_VALUES,
    _candidate_layer_surface_frame,
    _r2_input_payload,
)
from songryeon_core.runtime.terminal_view import render_runtime_view

from tests.test_order_184_r_vessel_multi_step_traversal import _record_packet
from tests.test_order_200_vessel_r_live_gated_integration import _run_live_vessel_turn


def test_r2_payload_supplies_explicit_granularity_enum_contract() -> None:
    _, _, _, packet = _record_packet(entry_rows=[], summary_rows=[])
    r1 = R1GraphGoalFrame(
        frame_id="R1:order_201:goal",
        graph_search_goal="Vessel R granularity contract 확인",
        required_information_granularity="low_summary",
        allowed_summary_depth=1,
        max_traversal_depth=6,
        max_branch_switches=0,
        max_node_reads=6,
        max_context_tokens=8000,
        stop_condition="Stop after relevant material is found.",
        source_graph_guide_packet_id=packet.packet_id,
        user_question_anchor_id="anchor:test",
        source_data_ids=[packet.packet_id],
        source_trace_ids=[],
    )
    surface = _candidate_layer_surface_frame(
        frame_label="order_201",
        read_packet=packet,
        created_at="2026-07-04T00:00:00",
    )

    payload = _r2_input_payload(
        user_question="그래프 기억 구조를 설명해줘",
        read_packet=packet,
        r1=r1,
        candidate_layer_surface=surface,
        available_graph_node_ids=[],
    )

    assert payload["allowed_information_granularity_values"] == (
        R_INFORMATION_GRANULARITY_ENUM_VALUES
    )
    assert payload["expected_information_granularity_contract"] == {
        "output_field": "expected_information_granularity",
        "copy_exactly_from": "allowed_information_granularity_values",
        "no_free_text": True,
    }


def test_vessel_r_live_route_path_and_terminal_display_are_distinct() -> None:
    result = _run_live_vessel_turn(enable_vessel_r_route=True)

    route_path = result["route2_handoff_path"]
    assert "1:route=R_vessel_experimental" in route_path
    assert "R:Vessel_R1_R2_R3_traverse" in route_path
    assert "R:R1_R2_R3_experimental_skeleton" not in route_path
    assert "1:route=2" in route_path
    assert result["turn_activity_graph_link_r_vessel_ledger_count"] == 1

    rendered = render_runtime_view(
        result,
        user_input="Vessel 그래프 기억 구조를 설명해줘",
    )
    assert "R_vessel_ledgers=1" in rendered
    assert "R:R1_R2_R3_experimental_skeleton" not in rendered
