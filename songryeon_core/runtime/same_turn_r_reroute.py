from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.trace_store import TraceStore


R_TOP_LEVEL_RUN_MEMORY_DATA_TYPE = "node_output:r_top_level_run_memory_frame"
R_TOP_LEVEL_RUN_FRAME_DATA_TYPE = "node_output:r_top_level_run_frame"
SAME_TURN_R_REROUTE_CONTROLLER_DATA_TYPE = (
    "node_output:same_turn_r_reroute_controller_frame"
)


@dataclass(frozen=True)
class SameTurnRReroutePolicy:
    """Vessel R 전체 실행 횟수만 제한하는 코드 정책."""

    enabled: bool = False
    max_r_runs_per_turn: int = 2

    @property
    def effective_max_r_runs_per_turn(self) -> int:
        if self.max_r_runs_per_turn < 1:
            raise ValueError("max_r_runs_per_turn must be positive")
        return min(self.max_r_runs_per_turn, 2)

    @property
    def v0_ceiling_applied(self) -> bool:
        return self.max_r_runs_per_turn > self.effective_max_r_runs_per_turn


@dataclass(frozen=True)
class RTopLevelRunMemoryFrame:
    """node_0이 R 전체 실행 하나를 다음 판단용으로 정리한 절대정보 봉투."""

    frame_id: str
    run_frame_id: str
    turn_id: str
    run_index: int
    target: str
    mode: str
    source_return_packet_id: str
    source_activity_ledger_frame_id: str
    source_traverse_result_frame_id: str
    prior_run_memory_frame_id: str | None
    return_status: str
    traverse_status: str
    r_loop_task_status: str
    failure_stage: str | None
    failure_type: str | None
    failure_reason: str | None
    required_material_level: str
    required_material_count: int
    evidence_contract_observed_count: int
    evidence_contract_status: str
    selected_graph_node_ids: list[str] = field(default_factory=list)
    inspected_graph_node_ids: list[str] = field(default_factory=list)
    evidence_contract_material_node_ids: list[str] = field(default_factory=list)
    terminal_material_seen_count: int = 0
    raw_original_material_seen_count: int = 0
    raw_original_text_read_count: int = 0
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = "CODE:NODE_0_R_TOP_LEVEL_RUN_MEMORY"
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = "RTopLevelRunMemoryFrame"
    schema_version: str = "0.1"


@dataclass(frozen=True)
class RTopLevelRunFrame:
    """같은 턴의 R 전체 실행을 run index로 찾기 위한 장부 표지."""

    frame_id: str
    turn_id: str
    run_index: int
    batch_id: str
    run_status: str
    source_return_memory_frame_id: str
    source_return_packet_id: str
    source_activity_ledger_frame_id: str
    source_traverse_result_frame_id: str
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = "CODE:R_TOP_LEVEL_RUN_LEDGER"
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = "RTopLevelRunFrame"
    schema_version: str = "0.1"


@dataclass(frozen=True)
class RecordedRTopLevelRunMemory:
    run_frame: RTopLevelRunFrame
    memory_frame: RTopLevelRunMemoryFrame
    trace_event_id: str
    data_ids: list[str]


@dataclass(frozen=True)
class SameTurnRRerouteDecision:
    """node_1 재판정 뒤 코드가 R 횟수 정책만 집행한 결과."""

    controller_id: str
    turn_id: str
    current_run_index: int
    next_run_index: int | None
    same_turn_r_reroute_enabled: bool
    max_r_runs_per_turn: int
    effective_max_r_runs_per_turn: int
    v0_ceiling_applied: bool
    node1_route: str
    node1_route_data_id: str
    controller_decision: str
    decision_reason: str
    same_turn_rerun_allowed: bool
    planned_next_route: str
    source_run_memory_frame_id: str
    condition_flags: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = "CODE:SAME_TURN_R_REROUTE_CONTROLLER"
    info_class: str = "absolute_policy_decision"
    semantic_judgement_status: str = "not_run"
    schema_name: str = "SameTurnRRerouteControllerFrame"
    schema_version: str = "0.1"


def r_top_level_run_frame_id(run_index: int) -> str:
    _validate_run_index(run_index)
    return f"R:run:{run_index:04d}:run_frame"


def r_top_level_run_memory_frame_id(run_index: int) -> str:
    _validate_run_index(run_index)
    return f"R:run:{run_index:04d}:node_0:return_memory_frame"


def r_reroute_controller_frame_id(run_index: int) -> str:
    _validate_run_index(run_index)
    return f"R:run:{run_index:04d}:reroute_controller_frame"


def r_return_route_data_id(*, run_index: int, route: str) -> str:
    _validate_run_index(run_index)
    if route not in {"L", "R", "2"}:
        raise ValueError(f"unknown R return route: {route}")
    return f"R:run:{run_index:04d}:return:route:{route}"


def r_live_batch_id(*, turn_id: str, run_index: int) -> str:
    _validate_run_index(run_index)
    safe_turn_id = re.sub(r"[^A-Za-z0-9_]+", "_", turn_id).strip("_")
    if not safe_turn_id:
        raise ValueError("turn_id must contain a usable R batch label")
    return f"{safe_turn_id}_vessel_r_live_run_{run_index:04d}"


def record_r_top_level_run_memory(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    run_index: int,
    batch_id: str,
    return_packet_id: str,
    activity_ledger_frame_id: str,
    traverse_result_frame_id: str,
    prior_run_memory_frame_id: str | None,
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> RecordedRTopLevelRunMemory:
    return_payload = _payload(data_store, return_packet_id)
    activity_payload = _payload(data_store, activity_ledger_frame_id)
    traverse_payload = _payload(data_store, traverse_result_frame_id)
    frame_id = r_top_level_run_memory_frame_id(run_index)
    run_frame_id = r_top_level_run_frame_id(run_index)
    frame_sources = _unique_strings(
        [
            return_packet_id,
            activity_ledger_frame_id,
            traverse_result_frame_id,
            prior_run_memory_frame_id,
            *source_data_ids,
        ]
    )
    memory_frame = RTopLevelRunMemoryFrame(
        frame_id=frame_id,
        run_frame_id=run_frame_id,
        turn_id=turn_id,
        run_index=run_index,
        target="node_1_and_next_R",
        mode="r_top_level_return_memory",
        source_return_packet_id=return_packet_id,
        source_activity_ledger_frame_id=activity_ledger_frame_id,
        source_traverse_result_frame_id=traverse_result_frame_id,
        prior_run_memory_frame_id=prior_run_memory_frame_id,
        return_status=_text(return_payload, "return_status", "failed"),
        traverse_status=_text(traverse_payload, "traverse_status", "failed"),
        r_loop_task_status=_text(traverse_payload, "r_loop_task_status", "failed"),
        failure_stage=_optional_text(traverse_payload.get("failure_stage")),
        failure_type=_optional_text(traverse_payload.get("failure_type")),
        failure_reason=_optional_text(traverse_payload.get("failure_reason")),
        required_material_level=_text(
            traverse_payload,
            "required_material_level",
            "overview",
        ),
        required_material_count=_int(traverse_payload, "required_material_count"),
        evidence_contract_observed_count=_int(
            traverse_payload,
            "evidence_contract_observed_count",
        ),
        evidence_contract_status=_text(
            traverse_payload,
            "evidence_contract_status",
            "not_applicable",
        ),
        selected_graph_node_ids=_string_list(
            activity_payload.get("selected_graph_node_ids")
        ),
        inspected_graph_node_ids=_string_list(
            activity_payload.get("inspected_graph_node_ids")
        ),
        evidence_contract_material_node_ids=_string_list(
            traverse_payload.get("evidence_contract_material_node_ids")
        ),
        terminal_material_seen_count=_int(
            traverse_payload,
            "terminal_material_seen_count",
        ),
        raw_original_material_seen_count=_int(
            traverse_payload,
            "raw_original_material_seen_count",
        ),
        raw_original_text_read_count=_int(
            traverse_payload,
            "raw_original_text_read_count",
        ),
        source_trace_ids=_unique_strings(source_trace_ids),
        source_data_ids=frame_sources,
    )
    run_status = (
        "completed"
        if memory_frame.traverse_status == "completed"
        else "failed"
    )
    run_frame = RTopLevelRunFrame(
        frame_id=run_frame_id,
        turn_id=turn_id,
        run_index=run_index,
        batch_id=batch_id,
        run_status=run_status,
        source_return_memory_frame_id=frame_id,
        source_return_packet_id=return_packet_id,
        source_activity_ledger_frame_id=activity_ledger_frame_id,
        source_traverse_result_frame_id=traverse_result_frame_id,
        source_trace_ids=memory_frame.source_trace_ids,
        source_data_ids=_unique_strings([frame_id, *frame_sources]),
    )
    _validate_run_memory_frame(memory_frame)
    _validate_run_frame(run_frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="memory_packet",
        input_ref=memory_frame.source_trace_ids,
        output_ref=[frame_id, run_frame_id],
        schema_status="passed",
    )
    _create_record(
        data_store=data_store,
        data_id=frame_id,
        data_type=R_TOP_LEVEL_RUN_MEMORY_DATA_TYPE,
        payload=asdict(memory_frame),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
    )
    _create_record(
        data_store=data_store,
        data_id=run_frame_id,
        data_type=R_TOP_LEVEL_RUN_FRAME_DATA_TYPE,
        payload=asdict(run_frame),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
    )
    return RecordedRTopLevelRunMemory(
        run_frame=run_frame,
        memory_frame=memory_frame,
        trace_event_id=event.event_id,
        data_ids=[frame_id, run_frame_id],
    )


def run_same_turn_r_reroute_controller(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    current_run_index: int,
    policy: SameTurnRReroutePolicy,
    node1_route: str,
    node1_route_data_id: str,
    run_memory_frame_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> tuple[str, str, SameTurnRRerouteDecision]:
    _validate_run_index(current_run_index)
    if node1_route not in {"L", "R", "2"}:
        raise ValueError(f"unknown node1 route after R: {node1_route}")

    next_run_index = current_run_index + 1
    allowed = False
    controller_decision = (
        "continue_L" if node1_route == "L" else "close_route_2"
    )
    decision_reason = (
        "CODE_STATUS:node1_selected_L_after_R"
        if node1_route == "L"
        else "CODE_STATUS:node1_selected_2_after_R"
    )
    planned_next_route = node1_route
    condition_flags = [decision_reason]

    if node1_route == "R":
        controller_decision = "close_route_2"
        planned_next_route = "2"
        if not policy.enabled:
            decision_reason = "CODE_STATUS:same_turn_R_reroute_disabled_by_policy"
        elif current_run_index >= policy.effective_max_r_runs_per_turn:
            decision_reason = "CODE_STATUS:same_turn_R_reroute_max_runs_reached"
        elif data_store.get_record(run_memory_frame_id) is None:
            decision_reason = "CODE_STATUS:missing_R_run_memory_for_reroute"
        elif data_store.get_record(node1_route_data_id) is None:
            decision_reason = "CODE_STATUS:missing_node1_R_return_route"
        elif _next_r_run_ids_collide(data_store, next_run_index):
            decision_reason = "CODE_STATUS:same_turn_R_reroute_next_run_id_collision"
        else:
            allowed = True
            controller_decision = "rerun_R"
            decision_reason = "CODE_STATUS:same_turn_R_reroute_allowed"
            planned_next_route = "R"
        condition_flags = [decision_reason]

    controller_id = r_reroute_controller_frame_id(current_run_index)
    frame = SameTurnRRerouteDecision(
        controller_id=controller_id,
        turn_id=turn_id,
        current_run_index=current_run_index,
        next_run_index=next_run_index if allowed else None,
        same_turn_r_reroute_enabled=policy.enabled,
        max_r_runs_per_turn=policy.max_r_runs_per_turn,
        effective_max_r_runs_per_turn=policy.effective_max_r_runs_per_turn,
        v0_ceiling_applied=policy.v0_ceiling_applied,
        node1_route=node1_route,
        node1_route_data_id=node1_route_data_id,
        controller_decision=controller_decision,
        decision_reason=decision_reason,
        same_turn_rerun_allowed=allowed,
        planned_next_route=planned_next_route,
        source_run_memory_frame_id=run_memory_frame_id,
        condition_flags=condition_flags,
        source_trace_ids=_unique_strings(source_trace_ids),
        source_data_ids=_unique_strings(
            [run_memory_frame_id, node1_route_data_id, *source_data_ids]
        ),
    )
    _validate_controller_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="R_reroute_controller",
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[controller_id],
        schema_status="passed",
    )
    _create_record(
        data_store=data_store,
        data_id=controller_id,
        data_type=SAME_TURN_R_REROUTE_CONTROLLER_DATA_TYPE,
        payload=asdict(frame),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
    )
    return event.event_id, controller_id, frame


def _next_r_run_ids_collide(data_store: DataStore, run_index: int) -> bool:
    return any(
        data_store.get_record(data_id) is not None
        for data_id in (
            r_top_level_run_frame_id(run_index),
            r_top_level_run_memory_frame_id(run_index),
            r_reroute_controller_frame_id(run_index),
        )
    )


def _validate_run_memory_frame(frame: RTopLevelRunMemoryFrame) -> None:
    _validate_run_index(frame.run_index)
    if frame.target != "node_1_and_next_R":
        raise ValueError("RTopLevelRunMemoryFrame.target is invalid")
    if frame.mode != "r_top_level_return_memory":
        raise ValueError("RTopLevelRunMemoryFrame.mode is invalid")
    if frame.info_class != "absolute" or frame.semantic_judgement_status != "not_run":
        raise ValueError("RTopLevelRunMemoryFrame metainfo boundary is invalid")
    for value in (
        frame.required_material_count,
        frame.evidence_contract_observed_count,
        frame.terminal_material_seen_count,
        frame.raw_original_material_seen_count,
        frame.raw_original_text_read_count,
    ):
        if value < 0:
            raise ValueError("RTopLevelRunMemoryFrame counts must not be negative")


def _validate_run_frame(frame: RTopLevelRunFrame) -> None:
    _validate_run_index(frame.run_index)
    if frame.run_status not in {"completed", "failed"}:
        raise ValueError("RTopLevelRunFrame.run_status is invalid")
    if frame.info_class != "absolute" or frame.semantic_judgement_status != "not_run":
        raise ValueError("RTopLevelRunFrame metainfo boundary is invalid")


def _validate_controller_frame(frame: SameTurnRRerouteDecision) -> None:
    _validate_run_index(frame.current_run_index)
    if not 1 <= frame.effective_max_r_runs_per_turn <= 2:
        raise ValueError("effective_max_r_runs_per_turn must be in range 1..2")
    if frame.controller_decision not in {"rerun_R", "continue_L", "close_route_2"}:
        raise ValueError("SameTurnRRerouteDecision.controller_decision is invalid")
    if frame.same_turn_rerun_allowed:
        if frame.node1_route != "R" or frame.planned_next_route != "R":
            raise ValueError("allowed R reroute must preserve node1 route R")
        if frame.next_run_index != frame.current_run_index + 1:
            raise ValueError("allowed R reroute must name the next run index")


def _payload(data_store: DataStore, data_id: str) -> dict[str, object]:
    record = data_store.require_record(data_id)
    if not isinstance(record.payload, dict):
        raise TypeError(f"{data_id} payload must be a dict")
    return record.payload


def _create_record(
    *,
    data_store: DataStore,
    data_id: str,
    data_type: str,
    payload: dict[str, object],
    created_at: str,
    source_trace_id: str,
) -> None:
    if data_store.get_record(data_id) is not None:
        raise ValueError(f"same-turn R data_id collision: {data_id}")
    data_store.create_record(
        data_id=data_id,
        data_type=data_type,
        exists=True,
        created_at=created_at,
        source_trace_id=source_trace_id,
        payload=payload,
    )


def _validate_run_index(run_index: int) -> None:
    if not isinstance(run_index, int) or isinstance(run_index, bool) or run_index < 1:
        raise ValueError("R run index must be a positive integer")


def _text(payload: dict[str, object], field_name: str, fallback: str) -> str:
    value = payload.get(field_name)
    return value if isinstance(value, str) and value else fallback


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _int(payload: dict[str, object], field_name: str) -> int:
    value = payload.get(field_name)
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return _unique_strings([item for item in value if isinstance(item, str)])


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


__all__ = [
    "RTopLevelRunFrame",
    "RTopLevelRunMemoryFrame",
    "RecordedRTopLevelRunMemory",
    "SameTurnRRerouteDecision",
    "SameTurnRReroutePolicy",
    "r_live_batch_id",
    "r_return_route_data_id",
    "r_reroute_controller_frame_id",
    "r_top_level_run_frame_id",
    "r_top_level_run_memory_frame_id",
    "record_r_top_level_run_memory",
    "run_same_turn_r_reroute_controller",
]
