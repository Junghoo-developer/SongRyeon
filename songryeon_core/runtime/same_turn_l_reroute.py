from __future__ import annotations

from dataclasses import asdict, dataclass, field

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.l_loop_namespace import LRunIds, build_l_run_ids


SAME_TURN_L_REROUTE_ALLOWED_REASON = (
    "CODE_STATUS:none_policy_guard_enabled_for_same_turn_L_reroute"
)
SAME_TURN_L_REROUTE_ENABLED_STEP = (
    "CODE_STATUS:same_turn_L_reroute_runtime_flow_enabled"
)
SAME_TURN_L_REROUTE_DISABLED_REASON = (
    "CODE_STATUS:same_turn_L_reroute_disabled_by_policy"
)
SAME_TURN_L_REROUTE_DISABLED_STEP = (
    "CODE_STATUS:same_turn_L_reroute_runtime_flow_closed_by_policy"
)
SAME_TURN_L_REROUTE_MAX_REACHED_REASON = (
    "CODE_STATUS:same_turn_L_reroute_max_runs_reached"
)
SAME_TURN_L_REROUTE_NODE1_ROUTE2_REASON = "CODE_STATUS:node1_selected_route_2"
SAME_TURN_L_REROUTE_MISSING_RETURN_SUMMARY_REASON = (
    "CODE_STATUS:missing_l_return_summary_for_reroute"
)
SAME_TURN_L_REROUTE_ID_COLLISION_REASON = (
    "CODE_STATUS:same_turn_L_reroute_next_run_id_collision"
)
SAME_TURN_L_REROUTE_ROUTE2_CLOSE_STEP = "CODE_STATUS:route_2_downstream_close_selected"
SAME_TURN_L_REROUTE_MAX_CLOSE_STEP = (
    "CODE_STATUS:route_2_downstream_close_after_same_turn_L_reroute_cap"
)
SAME_TURN_L_REROUTE_WAITING_STEP = (
    "CODE_STATUS:wait_for_node1_return_route_and_controller"
)


@dataclass(frozen=True)
class SameTurnLReroutePolicy:
    """Runtime policy for same-turn top-level L rerouting.

    v0 never opens a third L run. If a caller passes a larger max, the effective
    ceiling is still capped at 2 and that cap is recorded on controller frames.
    """

    enabled: bool = False
    max_l_runs_per_turn: int = 1

    @property
    def effective_max_l_runs_per_turn(self) -> int:
        if self.max_l_runs_per_turn < 1:
            raise ValueError("max_l_runs_per_turn must be positive")
        return min(self.max_l_runs_per_turn, 2)

    @property
    def v0_ceiling_applied(self) -> bool:
        return self.max_l_runs_per_turn > self.effective_max_l_runs_per_turn


@dataclass(frozen=True)
class SameTurnLRerouteDecision:
    """Controller result recorded after node_1 handles an L return."""

    controller_id: str
    turn_id: str
    current_run_index: int
    next_run_index: int | None
    same_turn_l_reroute_enabled: bool
    max_l_runs_per_turn: int
    effective_max_l_runs_per_turn: int
    v0_ceiling_applied: bool
    node1_route: str
    controller_decision: str
    decision_reason: str
    same_turn_rerun_allowed: bool
    planned_next_step: str
    condition_flags: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = "CODE:SAME_TURN_L_REROUTE_CONTROLLER"
    info_class: str = "absolute_policy_decision"
    semantic_judgement_status: str = "not_run"
    schema_name: str = "SameTurnLRerouteControllerFrame"
    schema_version: str = "0.1"


def run_same_turn_l_reroute_controller(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    run_ids: LRunIds,
    policy: SameTurnLReroutePolicy,
    node1_route: str,
    route_data_id: str,
    return_summary_data_id: str,
    return_packet_data_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> tuple[str, str, SameTurnLRerouteDecision]:
    """Record the code-only policy decision after an L return route.

    The controller checks only absolute runtime facts. It does not decide whether
    the user's goal is semantically satisfied.
    """

    existing_data_ids = {record.data_id for record in data_store.list_records()}
    next_run_index = run_ids.run_index + 1
    decision_name = "close_route_2"
    decision_reason = SAME_TURN_L_REROUTE_NODE1_ROUTE2_REASON
    allowed = False
    planned_next_step = SAME_TURN_L_REROUTE_ROUTE2_CLOSE_STEP
    condition_flags = [decision_reason]

    if node1_route == "L":
        if not policy.enabled:
            decision_reason = SAME_TURN_L_REROUTE_DISABLED_REASON
            planned_next_step = SAME_TURN_L_REROUTE_DISABLED_STEP
            condition_flags = [decision_reason]
        elif run_ids.run_index >= policy.effective_max_l_runs_per_turn:
            decision_reason = SAME_TURN_L_REROUTE_MAX_REACHED_REASON
            planned_next_step = SAME_TURN_L_REROUTE_MAX_CLOSE_STEP
            condition_flags = [decision_reason]
        elif return_summary_data_id not in existing_data_ids:
            decision_reason = SAME_TURN_L_REROUTE_MISSING_RETURN_SUMMARY_REASON
            planned_next_step = SAME_TURN_L_REROUTE_ROUTE2_CLOSE_STEP
            condition_flags = [decision_reason]
        elif return_packet_data_id not in existing_data_ids:
            decision_reason = "CODE_STATUS:missing_l_return_memory_packet_for_reroute"
            planned_next_step = SAME_TURN_L_REROUTE_ROUTE2_CLOSE_STEP
            condition_flags = [decision_reason]
        elif route_data_id not in existing_data_ids:
            decision_reason = "CODE_STATUS:missing_node1_return_route_for_reroute"
            planned_next_step = SAME_TURN_L_REROUTE_ROUTE2_CLOSE_STEP
            condition_flags = [decision_reason]
        else:
            next_ids = build_l_run_ids(run_index=next_run_index)
            colliding_ids = _next_run_collision_ids(
                data_store=data_store,
                next_ids=next_ids,
                turn_id=turn_id,
            )
            if colliding_ids:
                decision_reason = SAME_TURN_L_REROUTE_ID_COLLISION_REASON
                planned_next_step = SAME_TURN_L_REROUTE_ROUTE2_CLOSE_STEP
                condition_flags = [decision_reason, *[f"collision:{item}" for item in colliding_ids]]
            else:
                decision_name = "rerun_L"
                decision_reason = SAME_TURN_L_REROUTE_ALLOWED_REASON
                allowed = True
                planned_next_step = SAME_TURN_L_REROUTE_ENABLED_STEP
                condition_flags = [
                    "same_turn_l_reroute_enabled",
                    "current_run_below_max",
                    "l_return_summary_present",
                    "l_return_memory_packet_present",
                    "node1_return_route_present",
                    "next_l_run_ids_available",
                    "next_l_run_ids_not_colliding",
                ]

    controller_id = run_ids.reroute_controller_data_id()
    frame = SameTurnLRerouteDecision(
        controller_id=controller_id,
        turn_id=turn_id,
        current_run_index=run_ids.run_index,
        next_run_index=next_run_index if allowed else None,
        same_turn_l_reroute_enabled=policy.enabled,
        max_l_runs_per_turn=policy.max_l_runs_per_turn,
        effective_max_l_runs_per_turn=policy.effective_max_l_runs_per_turn,
        v0_ceiling_applied=policy.v0_ceiling_applied,
        node1_route=node1_route,
        controller_decision=decision_name,
        decision_reason=decision_reason,
        same_turn_rerun_allowed=allowed,
        planned_next_step=planned_next_step,
        condition_flags=condition_flags,
        source_trace_ids=_unique_strings(source_trace_ids),
        source_data_ids=_unique_strings(source_data_ids),
    )
    _validate_controller_frame(frame)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="L_reroute_controller",
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[controller_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=controller_id,
        data_type="node_output:same_turn_l_reroute_controller_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, controller_id, frame


def _next_run_collision_ids(
    *,
    data_store: DataStore,
    next_ids: LRunIds,
    turn_id: str,
) -> list[str]:
    candidates = [
        next_ids.run_frame_data_id,
        next_ids.l1_goal_data_id,
        next_ids.l2_query_plan_data_id,
        next_ids.l2_query_data_id,
        next_ids.l3_preserved_data_id,
        next_ids.l3_achievement_data_id,
        next_ids.budget_plan_data_id,
        next_ids.return_summary_frame_id(),
        next_ids.loop_return_memory_packet_id(),
        next_ids.route_decision_id("L"),
        next_ids.route_decision_id("2"),
        next_ids.memory_packet_data_id(target="L", mode="targeted_memory_supply"),
        next_ids.memory_packet_data_id(target="node_2", mode="final_trace_for_2"),
        next_ids.turn_outcome_id(turn_id),
        next_ids.node2_input_frame_id(turn_id),
        next_ids.route2_handoff_frame_id(),
        next_ids.metainfo_boundary_id(),
        next_ids.node3_input_brief_frame_id(),
        next_ids.node3_report_id(),
        next_ids.node4_gatekeeper_frame_id(),
    ]
    return [data_id for data_id in candidates if data_store.get_record(data_id) is not None]


def _validate_controller_frame(frame: SameTurnLRerouteDecision) -> None:
    for field_name, value in {
        "controller_id": frame.controller_id,
        "turn_id": frame.turn_id,
        "node1_route": frame.node1_route,
        "controller_decision": frame.controller_decision,
        "decision_reason": frame.decision_reason,
        "planned_next_step": frame.planned_next_step,
        "generated_by": frame.generated_by,
        "info_class": frame.info_class,
        "semantic_judgement_status": frame.semantic_judgement_status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"SameTurnLRerouteDecision.{field_name} must not be empty")
    if frame.node1_route not in {"L", "2"}:
        raise ValueError(f"unknown node1 route: {frame.node1_route}")
    if frame.controller_decision not in {"rerun_L", "close_route_2"}:
        raise ValueError(f"unknown same-turn L reroute decision: {frame.controller_decision}")
    if frame.current_run_index < 1:
        raise ValueError("current_run_index must be positive")
    if frame.max_l_runs_per_turn < 1:
        raise ValueError("max_l_runs_per_turn must be positive")
    if frame.effective_max_l_runs_per_turn < 1 or frame.effective_max_l_runs_per_turn > 2:
        raise ValueError("effective_max_l_runs_per_turn must be in v0 range 1..2")
    if frame.same_turn_rerun_allowed and frame.next_run_index != frame.current_run_index + 1:
        raise ValueError("allowed reroute must name the next L run index")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("source_data_ids must not contain empty values")


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
