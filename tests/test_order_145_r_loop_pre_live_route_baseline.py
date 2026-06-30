from __future__ import annotations

import pytest

from songryeon_core.core.schemas import (
    MemoryPacketFrom0,
    RoutingDecisionFrame,
    validate_routing_decision_frame,
)
from songryeon_core.nodes.node_1_router import _validate_llm_routing_payload, route_next
from songryeon_core.core.registry import build_default_schema_registry
from songryeon_core.runtime.dry_run import run_dry_turn


def test_pre_live_route_r_is_not_allowed_by_routing_frame_validator() -> None:
    frame = RoutingDecisionFrame(
        frame_id="route:R",
        turn_id="turn_order_145",
        route="R",
        route_reason="CODE_STATUS:test_r_route_not_live",
        expected_next_0_mode="r_loop_memory_supply",
    )

    with pytest.raises(ValueError, match="experimental policy flag"):
        validate_routing_decision_frame(frame)


def test_pre_live_node1_llm_payload_rejects_route_r() -> None:
    payload = {
        "route": "R",
        "route_reason": "LLM wanted graph traversal",
        "expected_next_0_mode": "r_loop_memory_supply",
    }

    with pytest.raises(ValueError, match="node_1 route must be L or 2"):
        _validate_llm_routing_payload(payload)


def test_pre_live_policy_router_still_outputs_only_l_or_2() -> None:
    registry = build_default_schema_registry()
    memory_packet = MemoryPacketFrom0(target="node_1")

    default_decision = route_next(
        user_input="안녕",
        memory_packet=memory_packet,
        schema_registry=registry,
    )
    l_decision = route_next(
        user_input="송련 내부 문서를 검색해줘",
        memory_packet=memory_packet,
        schema_registry=registry,
    )

    assert default_decision.route == "2"
    assert l_decision.route == "L"


def test_pre_live_default_dry_run_records_no_r_route_skeleton() -> None:
    result = run_dry_turn()

    assert result["r_route_dry_run_enabled"] is False
    assert result["r_route_dry_run_status"] == "not_run"
    assert result["r_route_dry_run_output_data_ids"] == []
    assert not _payloads_with_type(result, "node_output:R_loop_return_summary_frame")


def test_pre_live_opt_in_r_dry_run_frames_remain_code_generated_not_run() -> None:
    result = run_dry_turn(enable_r_route_dry_run=True)

    assert result["r_route_dry_run_enabled"] is True
    assert result["r_route_dry_run_status"] == "partial"

    r_payloads = [
        payload
        for payload in _all_payloads(result)
        if str(payload.get("frame_id", "")).startswith("R")
    ]
    assert r_payloads
    for payload in r_payloads:
        assert payload.get("generated_by") == "CODE:R_LOOP_DRY_RUN_ONLY"
        assert payload.get("semantic_judgement_status") == "not_run"


def test_pre_live_r_dry_run_control_frames_are_absolute() -> None:
    result = run_dry_turn(enable_r_route_dry_run=True)

    control_types = {
        "node_output:R_loop_budget_frame",
        "node_output:R_loop_continuation_frame",
        "node_output:R_loop_return_summary_frame",
    }
    control_payloads = [
        record["payload"]
        for record in result["data_records"]
        if record["data_type"] in control_types
    ]

    assert len(control_payloads) == 3
    for payload in control_payloads:
        assert payload["generated_by"] == "CODE:R_LOOP_DRY_RUN_ONLY"
        assert payload["info_class"] == "absolute"
        assert payload["semantic_judgement_status"] == "not_run"


def test_pre_live_r_dry_run_output_is_not_injected_into_node1_or_node3() -> None:
    result = run_dry_turn(enable_r_route_dry_run=True)
    r_data_ids = set(result["r_route_dry_run_output_data_ids"])
    r_data_ids.add(result["r_loop_memory_handoff_packet_id"])

    for record in result["data_records"]:
        if record["data_type"] not in {
            "node_output:routing_decision",
            "node_output:report",
        }:
            continue
        source_data_ids = set(record["payload"].get("source_data_ids", []))
        assert not (source_data_ids & r_data_ids)


def _all_payloads(result: dict[str, object]) -> list[dict[str, object]]:
    records = result.get("data_records")
    if not isinstance(records, list):
        return []
    payloads: list[dict[str, object]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        payload = record.get("payload")
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _payloads_with_type(result: dict[str, object], data_type: str) -> list[dict[str, object]]:
    records = result.get("data_records")
    if not isinstance(records, list):
        return []
    payloads: list[dict[str, object]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("data_type") != data_type:
            continue
        payload = record.get("payload")
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads
