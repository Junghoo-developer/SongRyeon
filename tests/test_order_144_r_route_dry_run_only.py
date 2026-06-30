from __future__ import annotations

import pytest

from songryeon_core.core.schemas import (
    R2GraphNodeSelectionFrame,
    validate_r2_graph_node_selection_frame,
)
from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.terminal_view import render_runtime_view


def test_default_dry_run_does_not_open_r_route_skeleton() -> None:
    result = run_dry_turn()

    assert result["current_route"] in {"2", "L"}
    assert result["r_route_dry_run_enabled"] is False
    assert result["r_route_dry_run_status"] == "not_run"
    assert result["r_route_dry_run_output_data_ids"] == []
    assert not _payloads_with_type(result, "node_output:R_loop_return_summary_frame")


def test_r_route_dry_run_fixture_records_r1_r2_r3_continuation_and_summary() -> None:
    result = run_dry_turn(enable_r_route_dry_run=True)

    assert result["r_route_dry_run_enabled"] is True
    assert result["r_route_dry_run_status"] == "partial"
    assert result["r_route_dry_run_continuation_status"] == "continue_deeper"
    assert result["r_route_dry_run_next_target_node"] == "R2"
    assert result["r_route_dry_run_budget_status"] == "within_budget"
    assert result["r_route_dry_run_selected_entry_node_ids"] == ["graph:axis:time"]
    assert result["r_route_dry_run_inspected_graph_node_ids"] == ["graph:axis:time"]

    assert len(_payloads_with_type(result, "node_output:R1_graph_goal_frame")) == 1
    assert len(_payloads_with_type(result, "node_output:R_loop_budget_frame")) == 1
    assert len(_payloads_with_type(result, "node_output:R2_graph_node_selection_frame")) == 1
    assert len(_payloads_with_type(result, "node_output:R3_graph_inspection_frame")) == 1
    assert len(_payloads_with_type(result, "node_output:R_loop_continuation_frame")) == 1
    assert len(_payloads_with_type(result, "node_output:R_loop_return_summary_frame")) == 1

    summary = _payloads_with_type(result, "node_output:R_loop_return_summary_frame")[0]
    handoff_id = result["r_loop_memory_handoff_packet_id"]
    assert handoff_id in summary["source_data_ids"]
    assert summary["generated_by"] == "CODE:R_LOOP_DRY_RUN_ONLY"
    assert summary["info_class"] == "absolute"
    assert summary["semantic_judgement_status"] == "not_run"


def test_r_route_dry_run_r2_selection_accepts_only_available_graph_node_id() -> None:
    selected = _r2_selection(selected_graph_node_id="graph:axis:time")
    validate_r2_graph_node_selection_frame(selected)

    invalid = _r2_selection(selected_graph_node_id="graph:axis:semantic")
    with pytest.raises(ValueError, match="selected_graph_node_id must be available"):
        validate_r2_graph_node_selection_frame(invalid)


def test_r_route_dry_run_budget_exhaustion_closes_with_stop_budget_exhausted() -> None:
    result = run_dry_turn(
        enable_r_route_dry_run=True,
        r_route_dry_run_force_budget_exhausted=True,
    )

    assert result["r_route_dry_run_status"] == "partial"
    assert result["r_route_dry_run_continuation_status"] == "stop_budget_exhausted"
    assert result["r_route_dry_run_next_target_node"] == "return_summary"
    assert result["r_route_dry_run_budget_status"] == "exhausted"

    continuation = _payloads_with_type(result, "node_output:R_loop_continuation_frame")[0]
    assert continuation["remaining_node_reads"] == 0
    assert continuation["continuation_reason_code"] == (
        "CODE_STATUS:r_loop_node_or_context_budget_exhausted"
    )


def test_terminal_runtime_displays_r_dry_run_as_code_only_when_enabled() -> None:
    disabled = render_runtime_view(run_dry_turn(), user_input="R dry run disabled")
    assert "- R dry-run skeleton" not in disabled

    enabled_result = run_dry_turn(enable_r_route_dry_run=True)
    enabled = render_runtime_view(enabled_result, user_input="R dry run enabled")
    assert "- R dry-run skeleton [CODE:R_LOOP_DRY_RUN_ONLY]:" in enabled
    assert "task_status=partial" in enabled
    assert "continuation=continue_deeper" in enabled
    assert "semantic_judgement_status: not_run" in enabled


def test_r_route_dry_run_does_not_inject_r_frames_into_node1_or_node3() -> None:
    result = run_dry_turn(enable_r_route_dry_run=True)
    r_data_ids = set(result["r_route_dry_run_output_data_ids"])
    r_data_ids.add(result["r_loop_memory_handoff_packet_id"])

    for record in result["data_records"]:
        if record["data_type"] not in {"node_output:routing_decision", "node_output:report"}:
            continue
        source_data_ids = set(record["payload"].get("source_data_ids", []))
        assert not (source_data_ids & r_data_ids)


def _r2_selection(*, selected_graph_node_id: str) -> R2GraphNodeSelectionFrame:
    return R2GraphNodeSelectionFrame(
        frame_id="R2:dry_run:test_selection",
        selection_scope="test_scope",
        available_graph_node_ids=["graph:axis:time"],
        selection_status="selected",
        selected_graph_node_id=selected_graph_node_id,
        selection_reason="CODE_STATUS:test_selection",
        expected_information_granularity="unknown",
        expected_source_kind="graph_entry_node",
        source_r1_goal_frame_id="R1:dry_run:graph_goal_frame",
        source_data_ids=["R1:dry_run:graph_goal_frame"],
    )


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
