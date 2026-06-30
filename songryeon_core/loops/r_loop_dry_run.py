from __future__ import annotations

from dataclasses import asdict, dataclass

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_state_machine import decide_r_loop_continuation
from songryeon_core.core.schemas import (
    R1GraphGoalFrame,
    R2GraphNodeSelectionFrame,
    R3GraphInspectionFrame,
    RLoopBudgetFrame,
    RLoopContinuationFrame,
    RLoopMemoryHandoffPacketFrame,
    RLoopReturnSummaryFrame,
    validate_r1_graph_goal_frame,
    validate_r2_graph_node_selection_frame,
    validate_r3_graph_inspection_frame,
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
    continuation: RLoopContinuationFrame
    return_summary: RLoopReturnSummaryFrame
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
    budget = _build_budget(
        r1=r1,
        force_budget_exhausted=force_budget_exhausted,
        frame_label=frame_label,
        generated_by=generated_by,
    )
    r2 = _build_r2_selection(
        handoff_packet=handoff_packet,
        r1=r1,
        frame_label=frame_label,
        generated_by=generated_by,
    )
    r3 = _build_r3_inspection(
        data_store=data_store,
        handoff_packet=handoff_packet,
        r2=r2,
        frame_label=frame_label,
        generated_by=generated_by,
    )
    continuation = decide_r_loop_continuation(
        frame_id=f"R:{frame_label}:continuation_frame:0001",
        r3_inspection=r3,
        budget=budget,
        source_trace_ids=input_ref or [],
    )
    continuation.generated_by = generated_by
    validate_r_loop_continuation_frame(continuation)
    summary = _build_return_summary(
        handoff_packet=handoff_packet,
        r1=r1,
        budget=budget,
        r2=r2,
        r3=r3,
        continuation=continuation,
        frame_label=frame_label,
        generated_by=generated_by,
    )

    frames: list[tuple[str, str, object]] = [
        ("R1", "node_output:R1_graph_goal_frame", r1),
        ("R:budget", "node_output:R_loop_budget_frame", budget),
        ("R2", "node_output:R2_graph_node_selection_frame", r2),
        ("R3", "node_output:R3_graph_inspection_frame", r3),
        ("R:continuation", "node_output:R_loop_continuation_frame", continuation),
        ("R:return_summary", "node_output:R_loop_return_summary_frame", summary),
    ]
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
        continuation=continuation,
        return_summary=summary,
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
) -> RLoopBudgetFrame:
    used_node_reads = r1.max_node_reads if force_budget_exhausted else 1
    frame = RLoopBudgetFrame(
        frame_id=f"R:{frame_label}:budget_frame",
        source_r1_goal_frame_id=r1.frame_id,
        max_traversal_depth=r1.max_traversal_depth,
        max_branch_switches=r1.max_branch_switches,
        max_node_reads=r1.max_node_reads,
        max_context_tokens=r1.max_context_tokens,
        used_traversal_depth=1,
        used_branch_switches=0,
        used_node_reads=used_node_reads,
        used_context_tokens=240,
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
    frame_label: str,
    generated_by: str,
) -> R2GraphNodeSelectionFrame:
    selected_id = handoff_packet.available_entry_node_ids[0]
    frame = R2GraphNodeSelectionFrame(
        frame_id=f"R2:{frame_label}:graph_node_selection_frame",
        selection_scope="core_ego_graph_guide_handoff",
        available_graph_node_ids=list(handoff_packet.available_entry_node_ids),
        selection_status="selected",
        selected_graph_node_id=selected_id,
        selection_reason=f"CODE_STATUS:{frame_label}_select_first_available_entry_node",
        expected_information_granularity="unknown",
        expected_source_kind="graph_entry_node",
        source_r1_goal_frame_id=r1.frame_id,
        source_data_ids=[r1.frame_id, handoff_packet.packet_id],
        source_trace_ids=list(handoff_packet.source_trace_ids),
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
) -> R3GraphInspectionFrame:
    selected_id = r2.selected_graph_node_id
    if selected_id is None:
        raise ValueError("R dry-run R2 selection did not select a graph node")
    node_payload = _graph_node_payload(data_store=data_store, node_id=selected_id)
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
        frame_id=f"R3:{frame_label}:graph_inspection_frame",
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


def _build_return_summary(
    *,
    handoff_packet: RLoopMemoryHandoffPacketFrame,
    r1: R1GraphGoalFrame,
    budget: RLoopBudgetFrame,
    r2: R2GraphNodeSelectionFrame,
    r3: R3GraphInspectionFrame,
    continuation: RLoopContinuationFrame,
    frame_label: str,
    generated_by: str,
) -> RLoopReturnSummaryFrame:
    if continuation.continuation_status == "stop_sufficient":
        task_status = "sufficient"
    elif continuation.continuation_status == "stop_failed_final":
        task_status = "failed"
    else:
        task_status = "partial"
    selected_entry_node_ids = (
        [r2.selected_graph_node_id] if r2.selected_graph_node_id is not None else []
    )
    frame = RLoopReturnSummaryFrame(
        frame_id=f"R:{frame_label}:return_summary_frame",
        r_loop_task_status=task_status,
        selected_entry_node_ids=selected_entry_node_ids,
        inspected_graph_node_ids=[r3.inspected_graph_node_id],
        final_information_granularity=r3.current_information_granularity,
        summary_depth_used=r3.summary_depth,
        continuation_status=continuation.continuation_status,
        budget_status=budget.budget_status,
        source_graph_node_ids=_unique_strings(
            [
                *selected_entry_node_ids,
                r3.inspected_graph_node_id,
                *r3.child_node_ids,
                *handoff_packet.source_graph_node_ids,
            ]
        ),
        source_data_ids=_unique_strings(
            [
                handoff_packet.packet_id,
                r1.frame_id,
                budget.frame_id,
                r2.frame_id,
                r3.frame_id,
                continuation.frame_id,
            ]
        ),
        source_trace_ids=_unique_strings(
            [
                *handoff_packet.source_trace_ids,
                *continuation.source_trace_ids,
            ]
        ),
        generated_by=generated_by,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )
    validate_r_loop_return_summary_frame(frame)
    return frame


def _safe_frame_label(value: str) -> str:
    normalized = value.strip().replace("-", "_").replace(" ", "_")
    if not normalized:
        return "dry_run"
    if not all(ch.isalnum() or ch == "_" for ch in normalized):
        raise ValueError("R loop frame_label must contain only letters, numbers, or underscore")
    return normalized


def _graph_node_payload(*, data_store: DataStore, node_id: str) -> dict[str, object]:
    record = data_store.get_record(node_id)
    if record is None:
        return {}
    if not isinstance(record.payload, dict):
        raise TypeError(f"graph node payload must be a dict: {node_id}")
    return record.payload


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
