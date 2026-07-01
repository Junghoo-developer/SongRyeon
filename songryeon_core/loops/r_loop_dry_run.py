from __future__ import annotations

from dataclasses import asdict, dataclass

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import raw_capsule_graph_node_id
from songryeon_core.core.r_loop_state_machine import decide_r_loop_continuation
from songryeon_core.core.schemas import (
    R1GraphGoalFrame,
    R2GraphNodeSelectionFrame,
    R3GraphInspectionFrame,
    RGraphTraversalCandidateSurfaceFrame,
    RLoopBudgetFrame,
    RLoopContinuationFrame,
    RLoopMemoryHandoffPacketFrame,
    RLoopReturnSummaryFrame,
    TurnGraphAccessLedgerFrame,
    validate_r1_graph_goal_frame,
    validate_r2_graph_node_selection_frame,
    validate_r3_graph_inspection_frame,
    validate_r_graph_traversal_candidate_surface_frame,
    validate_turn_graph_access_ledger_frame,
    validate_r_loop_budget_frame,
    validate_r_loop_continuation_frame,
    validate_r_loop_memory_handoff_packet_frame,
    validate_r_loop_return_summary_frame,
)
from songryeon_core.core.trace_store import TraceStore


R_DRY_RUN_GENERATOR = "CODE:R_LOOP_DRY_RUN_ONLY"
R_EXPERIMENTAL_ROUTE_GENERATOR = "CODE:R_ROUTE_EXPERIMENTAL_GATE"


@dataclass
class RLoopDryRunResult:
    r1_goal: R1GraphGoalFrame
    budget: RLoopBudgetFrame
    r2_selection: R2GraphNodeSelectionFrame
    r3_inspection: R3GraphInspectionFrame
    candidate_surface: RGraphTraversalCandidateSurfaceFrame
    continuation: RLoopContinuationFrame
    return_summary: RLoopReturnSummaryFrame
    access_ledger: TurnGraphAccessLedgerFrame
    budgets: list[RLoopBudgetFrame]
    r2_selections: list[R2GraphNodeSelectionFrame]
    r3_inspections: list[R3GraphInspectionFrame]
    candidate_surfaces: list[RGraphTraversalCandidateSurfaceFrame]
    continuations: list[RLoopContinuationFrame]
    trace_event_ids: list[str]
    output_data_ids: list[str]


def run_r_loop_dry_run_skeleton(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    handoff_packet: RLoopMemoryHandoffPacketFrame,
    input_ref: list[str] | None = None,
    force_budget_exhausted: bool = False,
    frame_label: str = "dry_run",
    generated_by: str = R_DRY_RUN_GENERATOR,
    graph_node_payloads: dict[str, dict[str, object]] | None = None,
    graph_edge_payloads: list[dict[str, object]] | None = None,
) -> RLoopDryRunResult:
    """Run a deterministic R-loop skeleton for dry-run tests only."""

    validate_r_loop_memory_handoff_packet_frame(handoff_packet)
    if handoff_packet.packet_status != "available":
        raise ValueError("R dry-run skeleton requires an available graph guide handoff")

    frame_label = _safe_frame_label(frame_label)
    r1 = _build_r1_goal(
        handoff_packet=handoff_packet,
        frame_label=frame_label,
        generated_by=generated_by,
    )
    budgets: list[RLoopBudgetFrame] = []
    r2_selections: list[R2GraphNodeSelectionFrame] = []
    r3_inspections: list[R3GraphInspectionFrame] = []
    candidate_surfaces: list[RGraphTraversalCandidateSurfaceFrame] = []
    continuations: list[RLoopContinuationFrame] = []

    available_graph_node_ids = list(handoff_packet.available_entry_node_ids)
    previous_candidate_surface: RGraphTraversalCandidateSurfaceFrame | None = None
    for step_index in range(1, r1.max_node_reads + 1):
        if not available_graph_node_ids:
            break
        budget = _build_budget(
            r1=r1,
            force_budget_exhausted=force_budget_exhausted and step_index == 1,
            frame_label=frame_label,
            generated_by=generated_by,
            step_index=step_index,
        )
        r2 = _build_r2_selection(
            handoff_packet=handoff_packet,
            r1=r1,
            available_graph_node_ids=available_graph_node_ids,
            previous_candidate_surface=previous_candidate_surface,
            frame_label=frame_label,
            generated_by=generated_by,
            step_index=step_index,
        )
        r3 = _build_r3_inspection(
            data_store=data_store,
            handoff_packet=handoff_packet,
            r2=r2,
            frame_label=frame_label,
            generated_by=generated_by,
            step_index=step_index,
            graph_node_payloads=graph_node_payloads,
        )
        candidate_surface = _build_candidate_surface(
            data_store=data_store,
            r3=r3,
            frame_label=frame_label,
            step_index=step_index,
            graph_edge_payloads=graph_edge_payloads,
        )
        continuation = decide_r_loop_continuation(
            frame_id=f"R:{frame_label}:continuation_frame:{step_index:04d}",
            r3_inspection=r3,
            budget=budget,
            source_trace_ids=input_ref or [],
        )
        continuation.generated_by = generated_by
        validate_r_loop_continuation_frame(continuation)

        budgets.append(budget)
        r2_selections.append(r2)
        r3_inspections.append(r3)
        candidate_surfaces.append(candidate_surface)
        continuations.append(continuation)

        if continuation.continuation_status not in {
            "continue_deeper",
            "continue_switch_branch",
        }:
            break
        if continuation.next_target_node != "R2":
            break
        available_graph_node_ids = list(candidate_surface.candidate_graph_node_ids)
        previous_candidate_surface = candidate_surface

    if not budgets or not r2_selections or not r3_inspections or not candidate_surfaces or not continuations:
        raise ValueError("R dry-run skeleton did not produce traversal frames")

    budget = budgets[-1]
    r2 = r2_selections[-1]
    r3 = r3_inspections[-1]
    candidate_surface = candidate_surfaces[-1]
    continuation = continuations[-1]
    summary = _build_return_summary(
        handoff_packet=handoff_packet,
        r1=r1,
        budgets=budgets,
        r2_selections=r2_selections,
        r3_inspections=r3_inspections,
        candidate_surfaces=candidate_surfaces,
        continuation=continuation,
        frame_label=frame_label,
        generated_by=generated_by,
    )
    access_ledger = _build_access_ledger(
        turn_id=turn_id,
        handoff_packet=handoff_packet,
        r1=r1,
        budgets=budgets,
        r2_selections=r2_selections,
        r3_inspections=r3_inspections,
        candidate_surfaces=candidate_surfaces,
        continuation=continuation,
        summary=summary,
        frame_label=frame_label,
    )

    frames: list[tuple[str, str, object]] = [("R1", "node_output:R1_graph_goal_frame", r1)]
    for step_budget, step_r2, step_r3, step_surface, step_continuation in zip(
        budgets,
        r2_selections,
        r3_inspections,
        candidate_surfaces,
        continuations,
    ):
        frames.extend(
            [
                ("R:budget", "node_output:R_loop_budget_frame", step_budget),
                ("R2", "node_output:R2_graph_node_selection_frame", step_r2),
                ("R3", "node_output:R3_graph_inspection_frame", step_r3),
                (
                    "R:candidate_surface",
                    "node_output:R_graph_traversal_candidate_surface_frame",
                    step_surface,
                ),
                ("R:continuation", "node_output:R_loop_continuation_frame", step_continuation),
            ]
        )
    frames.extend(
        [
            ("R:return_summary", "node_output:R_loop_return_summary_frame", summary),
            ("R:access_ledger", "graph_memory:turn_access_ledger_frame", access_ledger),
        ]
    )
    trace_event_ids: list[str] = []
    output_data_ids: list[str] = []
    previous_trace_ids = list(input_ref or [])
    for actor, data_type, frame in frames:
        frame_payload = asdict(frame)
        frame_id = str(frame_payload["frame_id"])
        event = trace_store.create_event(
            turn_id=turn_id,
            actor=actor,
            event_type="node_output",
            input_ref=previous_trace_ids,
            output_ref=[frame_id],
            schema_status="passed",
        )
        data_store.create_record(
            data_id=frame_id,
            data_type=data_type,
            exists=True,
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            payload=frame_payload,
        )
        trace_event_ids.append(event.event_id)
        output_data_ids.append(frame_id)
        previous_trace_ids = [event.event_id]

    return RLoopDryRunResult(
        r1_goal=r1,
        budget=budget,
        r2_selection=r2,
        r3_inspection=r3,
        candidate_surface=candidate_surface,
        continuation=continuation,
        return_summary=summary,
        access_ledger=access_ledger,
        budgets=budgets,
        r2_selections=r2_selections,
        r3_inspections=r3_inspections,
        candidate_surfaces=candidate_surfaces,
        continuations=continuations,
        trace_event_ids=trace_event_ids,
        output_data_ids=output_data_ids,
    )


def _build_r1_goal(
    *,
    handoff_packet: RLoopMemoryHandoffPacketFrame,
    frame_label: str,
    generated_by: str,
) -> R1GraphGoalFrame:
    frame = R1GraphGoalFrame(
        frame_id=f"R1:{frame_label}:graph_goal_frame",
        graph_search_goal=f"CODE_STATUS:r_route_{frame_label}_inspect_graph_guide_handoff",
        required_information_granularity="unknown",
        allowed_summary_depth=max(handoff_packet.summary_depth_range),
        max_traversal_depth=2,
        max_branch_switches=1,
        max_node_reads=3,
        max_context_tokens=1200,
        stop_condition=f"CODE_STATUS:r_route_{frame_label}_stop_after_first_continuation_check",
        source_graph_guide_packet_id=handoff_packet.r_loop_graph_guide_packet_id,
        source_data_ids=_unique_strings(
            [
                handoff_packet.packet_id,
                handoff_packet.r_loop_graph_guide_packet_id,
                handoff_packet.graph_snapshot_id,
            ]
        ),
        source_trace_ids=list(handoff_packet.source_trace_ids),
        generated_by=generated_by,
        info_class="mixed",
        semantic_judgement_status="not_run",
    )
    validate_r1_graph_goal_frame(frame)
    return frame


def _build_budget(
    *,
    r1: R1GraphGoalFrame,
    force_budget_exhausted: bool,
    frame_label: str,
    generated_by: str,
    step_index: int,
) -> RLoopBudgetFrame:
    used_node_reads = r1.max_node_reads if force_budget_exhausted else step_index
    used_traversal_depth = (
        r1.max_traversal_depth
        if force_budget_exhausted
        else max(step_index - 1, 0)
    )
    used_context_tokens = (
        r1.max_context_tokens
        if force_budget_exhausted
        else min(240 * step_index, r1.max_context_tokens)
    )
    frame = RLoopBudgetFrame(
        frame_id=f"R:{frame_label}:budget_frame:{step_index:04d}",
        source_r1_goal_frame_id=r1.frame_id,
        max_traversal_depth=r1.max_traversal_depth,
        max_branch_switches=r1.max_branch_switches,
        max_node_reads=r1.max_node_reads,
        max_context_tokens=r1.max_context_tokens,
        used_traversal_depth=used_traversal_depth,
        used_branch_switches=0,
        used_node_reads=used_node_reads,
        used_context_tokens=used_context_tokens,
        budget_status="exhausted" if force_budget_exhausted else "within_budget",
        source_data_ids=[r1.frame_id],
        source_trace_ids=list(r1.source_trace_ids),
        generated_by=generated_by,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )
    validate_r_loop_budget_frame(frame)
    return frame


def _build_r2_selection(
    *,
    handoff_packet: RLoopMemoryHandoffPacketFrame,
    r1: R1GraphGoalFrame,
    available_graph_node_ids: list[str],
    previous_candidate_surface: RGraphTraversalCandidateSurfaceFrame | None,
    frame_label: str,
    generated_by: str,
    step_index: int,
) -> R2GraphNodeSelectionFrame:
    if not available_graph_node_ids:
        raise ValueError("R2 dry-run selection requires available graph node ids")
    selected_id = available_graph_node_ids[0]
    if previous_candidate_surface is None:
        selection_scope = "core_ego_graph_guide_handoff"
        expected_source_kind = "graph_entry_node"
        source_data_ids = [r1.frame_id, handoff_packet.packet_id]
        source_trace_ids = list(handoff_packet.source_trace_ids)
        reason = f"CODE_STATUS:{frame_label}_select_first_available_entry_node"
    else:
        selection_scope = "r_graph_traversal_candidate_surface"
        expected_source_kind = "graph_candidate_node"
        source_data_ids = [
            r1.frame_id,
            previous_candidate_surface.frame_id,
            *available_graph_node_ids,
        ]
        source_trace_ids = list(previous_candidate_surface.source_trace_ids)
        reason = f"CODE_STATUS:{frame_label}_select_first_candidate_surface_coordinate"
    frame = R2GraphNodeSelectionFrame(
        frame_id=f"R2:{frame_label}:graph_node_selection_frame:{step_index:04d}",
        selection_scope=selection_scope,
        available_graph_node_ids=list(available_graph_node_ids),
        selection_status="selected",
        selected_graph_node_id=selected_id,
        selection_reason=reason,
        expected_information_granularity="unknown",
        expected_source_kind=expected_source_kind,
        source_r1_goal_frame_id=r1.frame_id,
        source_data_ids=_unique_strings(source_data_ids),
        source_trace_ids=_unique_strings(source_trace_ids),
        generated_by=generated_by,
        info_class="mixed",
        semantic_judgement_status="not_run",
    )
    validate_r2_graph_node_selection_frame(frame)
    return frame


def _build_r3_inspection(
    *,
    data_store: DataStore,
    handoff_packet: RLoopMemoryHandoffPacketFrame,
    r2: R2GraphNodeSelectionFrame,
    frame_label: str,
    generated_by: str,
    step_index: int,
    graph_node_payloads: dict[str, dict[str, object]] | None = None,
) -> R3GraphInspectionFrame:
    selected_id = r2.selected_graph_node_id
    if selected_id is None:
        raise ValueError("R dry-run R2 selection did not select a graph node")
    node_payload = _graph_node_payload(
        data_store=data_store,
        node_id=selected_id,
        graph_node_payloads=graph_node_payloads,
    )
    if node_payload:
        child_node_ids = _string_list(node_payload.get("source_graph_node_ids"))
        node_kind = _text(node_payload.get("node_kind"), fallback="time_axis")
        summary_depth = _int(node_payload.get("summary_depth"))
        source_leaf_count = _int(node_payload.get("source_leaf_count"))
    else:
        child_node_ids = list(handoff_packet.source_graph_node_ids)
        node_kind = "time_axis"
        summary_depth = min(handoff_packet.summary_depth_range)
        source_leaf_count = max(handoff_packet.source_leaf_count_range)
    recommended_next_action = "deeper" if child_node_ids else "stop"
    granularity_status = "needs_lower_granularity" if child_node_ids else "none"
    sufficiency_status = "insufficient" if child_node_ids else "sufficient"
    frame = R3GraphInspectionFrame(
        frame_id=f"R3:{frame_label}:graph_inspection_frame:{step_index:04d}",
        inspected_graph_node_id=selected_id,
        node_kind=node_kind,
        child_node_count=len(child_node_ids),
        child_node_ids=child_node_ids,
        summary_depth=summary_depth,
        source_leaf_count=source_leaf_count,
        current_information_granularity="unknown",
        sufficiency_status=sufficiency_status,
        granularity_problem_status=granularity_status,
        branch_problem_status="none",
        recommended_next_action=recommended_next_action,
        inspection_reason=f"CODE_STATUS:{frame_label}_copied_graph_node_child_coordinates",
        source_r2_selection_frame_id=r2.frame_id,
        source_data_ids=[r2.frame_id, handoff_packet.packet_id, selected_id],
        source_trace_ids=list(handoff_packet.source_trace_ids),
        generated_by=generated_by,
        info_class="mixed",
        semantic_judgement_status="not_run",
    )
    validate_r3_graph_inspection_frame(frame)
    return frame


def _build_candidate_surface(
    *,
    data_store: DataStore,
    r3: R3GraphInspectionFrame,
    frame_label: str,
    step_index: int,
    graph_edge_payloads: list[dict[str, object]] | None = None,
) -> RGraphTraversalCandidateSurfaceFrame:
    next_edge_payloads = _graph_next_edge_payloads(
        data_store=data_store,
        from_node_id=r3.inspected_graph_node_id,
        graph_edge_payloads=graph_edge_payloads,
    )
    previous_edge_payloads = _graph_next_edge_payloads(
        data_store=data_store,
        to_node_id=r3.inspected_graph_node_id,
        graph_edge_payloads=graph_edge_payloads,
    )
    next_candidate_node_ids = _unique_strings(
        [_text(edge.get("to_node_id"), fallback="") for edge in next_edge_payloads]
    )
    previous_candidate_node_ids = _unique_strings(
        [_text(edge.get("from_node_id"), fallback="") for edge in previous_edge_payloads]
    )
    child_candidate_node_ids = _unique_strings(list(r3.child_node_ids))
    candidate_graph_node_ids = _unique_strings(
        [
            *child_candidate_node_ids,
            *next_candidate_node_ids,
            *previous_candidate_node_ids,
        ]
    )
    candidate_records: list[dict[str, str]] = []
    for graph_node_id in child_candidate_node_ids:
        candidate_records.append(
            {
                "candidate_node_id": graph_node_id,
                "relation": "child",
                "source_id": r3.frame_id,
                "source_field": "child_node_ids",
            }
        )
    for edge in next_edge_payloads:
        edge_id = _text(edge.get("edge_id"), fallback="")
        graph_node_id = _text(edge.get("to_node_id"), fallback="")
        if edge_id and graph_node_id:
            candidate_records.append(
                {
                    "candidate_node_id": graph_node_id,
                    "relation": "next",
                    "source_id": edge_id,
                    "source_field": "to_node_id",
                }
            )
    for edge in previous_edge_payloads:
        edge_id = _text(edge.get("edge_id"), fallback="")
        graph_node_id = _text(edge.get("from_node_id"), fallback="")
        if edge_id and graph_node_id:
            candidate_records.append(
                {
                    "candidate_node_id": graph_node_id,
                    "relation": "previous",
                    "source_id": edge_id,
                    "source_field": "from_node_id",
                }
            )
    source_data_ids = _unique_strings(
        [
            r3.frame_id,
            r3.inspected_graph_node_id,
            *child_candidate_node_ids,
            *next_candidate_node_ids,
            *previous_candidate_node_ids,
            *[_text(edge.get("edge_id"), fallback="") for edge in next_edge_payloads],
            *[_text(edge.get("edge_id"), fallback="") for edge in previous_edge_payloads],
        ]
    )
    source_trace_ids = _unique_strings(
        [
            *r3.source_trace_ids,
            *[
                trace_id
                for edge in [*next_edge_payloads, *previous_edge_payloads]
                for trace_id in _string_list(edge.get("source_trace_ids"))
            ],
        ]
    )
    frame = RGraphTraversalCandidateSurfaceFrame(
        frame_id=f"R:{frame_label}:graph_traversal_candidate_surface_frame:{step_index:04d}",
        source_r3_inspection_frame_id=r3.frame_id,
        inspected_graph_node_id=r3.inspected_graph_node_id,
        child_candidate_node_ids=child_candidate_node_ids,
        next_candidate_node_ids=next_candidate_node_ids,
        previous_candidate_node_ids=previous_candidate_node_ids,
        candidate_graph_node_ids=candidate_graph_node_ids,
        candidate_records=candidate_records,
        candidate_count=len(candidate_graph_node_ids),
        source_data_ids=source_data_ids,
        source_trace_ids=source_trace_ids,
    )
    validate_r_graph_traversal_candidate_surface_frame(frame)
    return frame


def _build_return_summary(
    *,
    handoff_packet: RLoopMemoryHandoffPacketFrame,
    r1: R1GraphGoalFrame,
    budgets: list[RLoopBudgetFrame],
    r2_selections: list[R2GraphNodeSelectionFrame],
    r3_inspections: list[R3GraphInspectionFrame],
    candidate_surfaces: list[RGraphTraversalCandidateSurfaceFrame],
    continuation: RLoopContinuationFrame,
    frame_label: str,
    generated_by: str,
) -> RLoopReturnSummaryFrame:
    if not budgets or not r2_selections or not r3_inspections or not candidate_surfaces:
        raise ValueError("R return summary requires traversal step frames")
    final_budget = budgets[-1]
    final_r3 = r3_inspections[-1]
    if continuation.continuation_status == "stop_sufficient":
        task_status = "sufficient"
    elif continuation.continuation_status == "stop_failed_final":
        task_status = "failed"
    else:
        task_status = "partial"
    selected_entry_node_ids = _unique_strings(
        [
            r2.selected_graph_node_id
            for r2 in r2_selections
            if r2.selected_graph_node_id is not None
        ]
    )
    inspected_graph_node_ids = _unique_strings(
        [r3.inspected_graph_node_id for r3 in r3_inspections]
    )
    frame = RLoopReturnSummaryFrame(
        frame_id=f"R:{frame_label}:return_summary_frame",
        r_loop_task_status=task_status,
        selected_entry_node_ids=selected_entry_node_ids,
        inspected_graph_node_ids=inspected_graph_node_ids,
        final_information_granularity=final_r3.current_information_granularity,
        summary_depth_used=final_r3.summary_depth,
        continuation_status=continuation.continuation_status,
        budget_status=final_budget.budget_status,
        source_graph_node_ids=_unique_strings(
            [
                *selected_entry_node_ids,
                *inspected_graph_node_ids,
                *[
                    child_id
                    for r3 in r3_inspections
                    for child_id in r3.child_node_ids
                ],
                *[
                    candidate_id
                    for surface in candidate_surfaces
                    for candidate_id in surface.candidate_graph_node_ids
                ],
                *handoff_packet.source_graph_node_ids,
            ]
        ),
        source_data_ids=_unique_strings(
            [
                handoff_packet.packet_id,
                r1.frame_id,
                *[budget.frame_id for budget in budgets],
                *[r2.frame_id for r2 in r2_selections],
                *[r3.frame_id for r3 in r3_inspections],
                *[surface.frame_id for surface in candidate_surfaces],
                continuation.frame_id,
            ]
        ),
        source_trace_ids=_unique_strings(
            [
                *handoff_packet.source_trace_ids,
                *continuation.source_trace_ids,
                *[
                    trace_id
                    for surface in candidate_surfaces
                    for trace_id in surface.source_trace_ids
                ],
            ]
        ),
        generated_by=generated_by,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )
    validate_r_loop_return_summary_frame(frame)
    return frame


def _build_access_ledger(
    *,
    turn_id: str,
    handoff_packet: RLoopMemoryHandoffPacketFrame,
    r1: R1GraphGoalFrame,
    budgets: list[RLoopBudgetFrame],
    r2_selections: list[R2GraphNodeSelectionFrame],
    r3_inspections: list[R3GraphInspectionFrame],
    candidate_surfaces: list[RGraphTraversalCandidateSurfaceFrame],
    continuation: RLoopContinuationFrame,
    summary: RLoopReturnSummaryFrame,
    frame_label: str,
) -> TurnGraphAccessLedgerFrame:
    candidate_graph_node_ids = _unique_strings(
        [
            *[
                graph_node_id
                for r2 in r2_selections
                for graph_node_id in r2.available_graph_node_ids
            ],
            *[
                child_id
                for r3 in r3_inspections
                for child_id in r3.child_node_ids
            ],
            *[
                candidate_id
                for surface in candidate_surfaces
                for candidate_id in surface.candidate_graph_node_ids
            ],
        ]
    )
    selected_graph_node_ids = _unique_strings(
        [
            r2.selected_graph_node_id
            for r2 in r2_selections
            if r2.selected_graph_node_id is not None
        ]
    )
    inspected_graph_node_ids = _unique_strings(
        [r3.inspected_graph_node_id for r3 in r3_inspections]
    )
    access_records: list[dict[str, str]] = []
    for r2 in r2_selections:
        for graph_node_id in r2.available_graph_node_ids:
            access_records.append(
                {
                    "stage": "candidate_seen",
                    "graph_node_id": graph_node_id,
                    "source_frame_id": r2.frame_id,
                    "source_field": "available_graph_node_ids",
                }
            )
        if r2.selected_graph_node_id is not None:
            access_records.append(
                {
                    "stage": "selected",
                    "graph_node_id": r2.selected_graph_node_id,
                    "source_frame_id": r2.frame_id,
                    "source_field": "selected_graph_node_id",
                }
            )
    for r3 in r3_inspections:
        access_records.append(
            {
                "stage": "inspected",
                "graph_node_id": r3.inspected_graph_node_id,
                "source_frame_id": r3.frame_id,
                "source_field": "inspected_graph_node_id",
            }
        )
        for graph_node_id in r3.child_node_ids:
            access_records.append(
                {
                    "stage": "candidate_seen",
                    "graph_node_id": graph_node_id,
                    "source_frame_id": r3.frame_id,
                    "source_field": "child_node_ids",
                }
            )
    for surface in candidate_surfaces:
        for record in surface.candidate_records:
            graph_node_id = record.get("candidate_node_id")
            if graph_node_id:
                access_records.append(
                    {
                        "stage": "candidate_seen",
                        "graph_node_id": graph_node_id,
                        "source_frame_id": surface.frame_id,
                        "source_field": f"candidate_records.{record.get('relation', 'unknown')}",
                    }
                )

    source_data_ids = _unique_strings(
        [
            handoff_packet.packet_id,
            handoff_packet.r_loop_graph_guide_packet_id,
            handoff_packet.graph_snapshot_id,
            r1.frame_id,
            *[budget.frame_id for budget in budgets],
            *[r2.frame_id for r2 in r2_selections],
            *[r3.frame_id for r3 in r3_inspections],
            *[surface.frame_id for surface in candidate_surfaces],
            continuation.frame_id,
            summary.frame_id,
            *candidate_graph_node_ids,
            *selected_graph_node_ids,
            *inspected_graph_node_ids,
        ]
    )
    frame = TurnGraphAccessLedgerFrame(
        frame_id=f"R:{frame_label}:turn_graph_access_ledger_frame",
        turn_id=turn_id,
        turn_capsule_graph_node_id=raw_capsule_graph_node_id(turn_id),
        candidate_graph_node_ids=candidate_graph_node_ids,
        selected_graph_node_ids=selected_graph_node_ids,
        inspected_graph_node_ids=inspected_graph_node_ids,
        read_graph_node_ids=[],
        used_as_answer_source_graph_node_ids=[],
        access_records=access_records,
        source_trace_ids=_unique_strings(
            [
                *handoff_packet.source_trace_ids,
                *continuation.source_trace_ids,
                *summary.source_trace_ids,
                *[
                    trace_id
                    for surface in candidate_surfaces
                    for trace_id in surface.source_trace_ids
                ],
            ]
        ),
        source_data_ids=source_data_ids,
    )
    validate_turn_graph_access_ledger_frame(frame)
    return frame


def _safe_frame_label(value: str) -> str:
    normalized = value.strip().replace("-", "_").replace(" ", "_")
    if not normalized:
        return "dry_run"
    if not all(ch.isalnum() or ch == "_" for ch in normalized):
        raise ValueError("R loop frame_label must contain only letters, numbers, or underscore")
    return normalized


def _graph_node_payload(
    *,
    data_store: DataStore,
    node_id: str,
    graph_node_payloads: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    if graph_node_payloads is not None:
        payload = graph_node_payloads.get(node_id)
        if payload is not None:
            return payload
    record = data_store.get_record(node_id)
    if record is None:
        return {}
    if not isinstance(record.payload, dict):
        raise TypeError(f"graph node payload must be a dict: {node_id}")
    return record.payload


def _graph_next_edge_payloads(
    *,
    data_store: DataStore,
    from_node_id: str | None = None,
    to_node_id: str | None = None,
    graph_edge_payloads: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    edge_payloads: list[dict[str, object]] = []
    for payload in graph_edge_payloads or []:
        if payload.get("edge_kind") != "NEXT":
            continue
        if from_node_id is not None and payload.get("from_node_id") != from_node_id:
            continue
        if to_node_id is not None and payload.get("to_node_id") != to_node_id:
            continue
        edge_payloads.append(payload)
    for record in data_store.list_records():
        if record.data_type != "graph_memory:edge:NEXT":
            continue
        if not isinstance(record.payload, dict):
            continue
        payload = record.payload
        if from_node_id is not None and payload.get("from_node_id") != from_node_id:
            continue
        if to_node_id is not None and payload.get("to_node_id") != to_node_id:
            continue
        edge_payloads.append(payload)
    return edge_payloads


def _text(value: object, *, fallback: str) -> str:
    return value if isinstance(value, str) and value else fallback


def _int(value: object) -> int:
    return value if isinstance(value, int) else 0


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item:
            result.append(item)
    return result


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
