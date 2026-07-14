from __future__ import annotations

import pytest

from songryeon_core.core.schemas import (
    R_ROUTE_CAPSULE_SKELETON_EXECUTION_MODE,
    R_ROUTE_CAPSULE_SKELETON_NEXT_0_MODE,
    R_ROUTE_EXPERIMENTAL_POLICY_FLAG,
    R_ROUTE_VESSEL_LIVE_EXECUTION_MODE,
    R_ROUTE_VESSEL_LIVE_NEXT_0_MODE,
    RoutingDecisionFrame,
    validate_routing_decision_frame,
)
from songryeon_core.nodes.node_1_router import _route_capability_cards


def test_node1_r_card_distinguishes_vessel_live_from_capsule_skeleton() -> None:
    vessel_card = _card_for_mode(R_ROUTE_VESSEL_LIVE_EXECUTION_MODE)
    skeleton_card = _card_for_mode(R_ROUTE_CAPSULE_SKELETON_EXECUTION_MODE)

    assert vessel_card["r_execution_mode"] == R_ROUTE_VESSEL_LIVE_EXECUTION_MODE
    assert vessel_card["expected_next_0_mode"] == R_ROUTE_VESSEL_LIVE_NEXT_0_MODE
    assert "Vessel read packet" in vessel_card["evidence_surface"]
    assert skeleton_card["r_execution_mode"] == R_ROUTE_CAPSULE_SKELETON_EXECUTION_MODE
    assert skeleton_card["expected_next_0_mode"] == R_ROUTE_CAPSULE_SKELETON_NEXT_0_MODE
    assert skeleton_card["raw_source_original_text_access"] == "not_available"
    assert "previous TurnStateCapsules" in skeleton_card["evidence_surface"]


def test_node1_route2_card_states_node2_is_not_a_recovery_or_blocking_node() -> None:
    cards = _route_capability_cards(allow_r_route_experimental=False)
    route2 = next(card for card in cards if card["route"] == "2")

    non_capabilities = " ".join(str(item) for item in route2["node_2_non_capabilities"])
    assert "does not reroute" in non_capabilities
    assert "does not itself block node_3" in non_capabilities
    assert route2["report_blocking_authority"] == "none_in_current_runtime"
    assert route2["recovery_capability"] == "none_in_current_runtime"
    assert "already supplied" in str(route2["selection_precondition"])


def test_routing_frame_rejects_execution_mode_and_first_node0_mode_mismatch() -> None:
    frame = _r_frame(
        route_execution_mode=R_ROUTE_VESSEL_LIVE_EXECUTION_MODE,
        expected_next_0_mode=R_ROUTE_CAPSULE_SKELETON_NEXT_0_MODE,
    )

    with pytest.raises(ValueError, match="does not match route_execution_mode"):
        validate_routing_decision_frame(frame)


def test_non_r_routing_frame_rejects_r_execution_mode() -> None:
    frame = RoutingDecisionFrame(
        frame_id="route:2",
        turn_id="turn_order_253_non_r",
        route="2",
        route_reason="already supplied material is enough",
        expected_next_0_mode="final_trace_for_2",
        route_execution_mode=R_ROUTE_VESSEL_LIVE_EXECUTION_MODE,
        route_source="LLM:test",
        llm_routing_status="ran",
        route_rule_id="llm_router",
    )

    with pytest.raises(ValueError, match="non-R"):
        validate_routing_decision_frame(frame)


def _card_for_mode(mode: str) -> dict[str, object]:
    cards = _route_capability_cards(
        allow_r_route_experimental=True,
        r_execution_mode=mode,
    )
    return next(card for card in cards if card["route"] == "R")


def _r_frame(
    *,
    route_execution_mode: str,
    expected_next_0_mode: str,
) -> RoutingDecisionFrame:
    return RoutingDecisionFrame(
        frame_id="route:R",
        turn_id="turn_order_253",
        route="R",
        route_reason="selected supplied R execution mode",
        expected_next_0_mode=expected_next_0_mode,
        route_execution_mode=route_execution_mode,
        route_source="LLM:test",
        llm_routing_status="ran",
        route_rule_id="llm_router",
        policy_flag=R_ROUTE_EXPERIMENTAL_POLICY_FLAG,
    )
