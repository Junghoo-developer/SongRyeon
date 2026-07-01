from __future__ import annotations

from songryeon_core.runtime.dry_run import run_dry_turn


def test_r_dry_run_consumes_candidate_surface_until_raw_capsule() -> None:
    result = run_dry_turn(enable_r_route_dry_run=True)

    assert result["r_route_dry_run_status"] == "sufficient"
    assert result["r_route_dry_run_continuation_status"] == "stop_sufficient"
    assert result["r_route_dry_run_traversal_step_count"] == 3
    assert result["r_route_dry_run_selected_entry_node_ids"] == [
        "graph:axis:time",
        "graph:time_bundle:turn_dry_001",
        "graph:raw_capsule:turn_dry_001",
    ]

    r2_frames = _payloads_with_type(result, "node_output:R2_graph_node_selection_frame")
    candidate_surfaces = _payloads_with_type(
        result,
        "node_output:R_graph_traversal_candidate_surface_frame",
    )
    continuations = _payloads_with_type(result, "node_output:R_loop_continuation_frame")

    assert [frame["selection_scope"] for frame in r2_frames] == [
        "core_ego_graph_guide_handoff",
        "r_graph_traversal_candidate_surface",
        "r_graph_traversal_candidate_surface",
    ]
    assert r2_frames[1]["selected_graph_node_id"] in candidate_surfaces[0][
        "candidate_graph_node_ids"
    ]
    assert r2_frames[2]["selected_graph_node_id"] in candidate_surfaces[1][
        "candidate_graph_node_ids"
    ]
    assert [frame["continuation_status"] for frame in continuations] == [
        "continue_deeper",
        "continue_deeper",
        "stop_sufficient",
    ]


def test_r_dry_run_budget_counts_entry_depth_as_zero_then_edges_as_depth() -> None:
    result = run_dry_turn(enable_r_route_dry_run=True)

    budgets = _payloads_with_type(result, "node_output:R_loop_budget_frame")

    assert [frame["used_node_reads"] for frame in budgets] == [1, 2, 3]
    assert [frame["used_traversal_depth"] for frame in budgets] == [0, 1, 2]
    assert [frame["budget_status"] for frame in budgets] == [
        "within_budget",
        "within_budget",
        "within_budget",
    ]


def test_r_dry_run_access_ledger_accumulates_multi_step_graph_nodes() -> None:
    result = run_dry_turn(enable_r_route_dry_run=True)

    ledger = _payloads_with_type(result, "graph_memory:turn_access_ledger_frame")[0]

    assert ledger["selected_graph_node_ids"] == [
        "graph:axis:time",
        "graph:time_bundle:turn_dry_001",
        "graph:raw_capsule:turn_dry_001",
    ]
    assert ledger["inspected_graph_node_ids"] == ledger["selected_graph_node_ids"]
    assert ledger["read_graph_node_ids"] == []
    assert ledger["used_as_answer_source_graph_node_ids"] == []
    assert ledger["generated_by"] == "CODE:GRAPH_ACCESS_LEDGER"
    assert ledger["semantic_judgement_status"] == "not_run"


def test_r_dry_run_forced_budget_exhaustion_still_stops_after_first_step() -> None:
    result = run_dry_turn(
        enable_r_route_dry_run=True,
        r_route_dry_run_force_budget_exhausted=True,
    )

    assert result["r_route_dry_run_status"] == "partial"
    assert result["r_route_dry_run_continuation_status"] == "stop_budget_exhausted"
    assert result["r_route_dry_run_traversal_step_count"] == 1
    assert len(_payloads_with_type(result, "node_output:R2_graph_node_selection_frame")) == 1
    assert len(_payloads_with_type(result, "node_output:R3_graph_inspection_frame")) == 1


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
