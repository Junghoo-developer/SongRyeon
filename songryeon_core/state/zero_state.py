from __future__ import annotations

from collections.abc import Iterable

from songryeon_core.core.schemas import NodeMovement, TurnStateCapsule, ZeroState
from songryeon_core.core.trace_store import TraceStore


def build_turn_capsule(
    trace_store: TraceStore,
    turn_id: str,
    *,
    node_movements: Iterable[NodeMovement] | None = None,
    user_input_trace_id: str | None = None,
    final_response_trace_id: str | None = None,
) -> TurnStateCapsule:
    """TraceStore의 한 턴 trace를 TurnStateCapsule로 묶는다."""

    # 이 함수는 요약이나 판단을 하지 않는다.
    # 특정 turn_id에 실제로 존재하는 trace ID를 모아 다음 턴의 0번이 다시 찾아볼 수 있게 묶는다.
    turn_events = trace_store.events_for_turn(turn_id)
    trace_event_ids = [event.event_id for event in turn_events]

    # 사용자 입력 trace ID가 명시되지 않으면, 해당 턴의 첫 user_input trace를 사용한다.
    # 없으면 None으로 둔다. 없는 값을 지어내지 않는 것이 0.state 원칙이다.
    resolved_user_input_trace_id = user_input_trace_id or _first_event_id_by_type(
        trace_store,
        turn_id,
        "user_input",
    )

    # 최종 응답 trace ID가 명시되지 않으면, 보수적으로 마지막 node_output trace를 후보로 삼는다.
    # 실제 3번 보고관이 생기면 actor나 event_type을 더 정확히 좁힐 수 있다.
    resolved_final_response_trace_id = final_response_trace_id or _last_event_id_by_type(
        trace_store,
        turn_id,
        "node_output",
    )

    movements = list(node_movements or [])
    _validate_node_movements(turn_id, movements)

    return TurnStateCapsule(
        turn_id=turn_id,
        node_movements=movements,
        trace_event_ids=trace_event_ids,
        user_input_trace_id=resolved_user_input_trace_id,
        final_response_trace_id=resolved_final_response_trace_id,
    )


def add_capsule_to_zero_state(
    zero_state: ZeroState,
    capsule: TurnStateCapsule,
    *,
    max_capsules: int | None = None,
) -> ZeroState:
    """생성된 턴 캡슐을 ZeroState.previous_turn_capsules에 추가한다."""

    # 기존 ZeroState 객체를 직접 갱신한다.
    # 지금은 단순함을 우선하고, 나중에 불변 상태 관리가 필요하면 별도 발주로 뺀다.
    zero_state.previous_turn_capsules.append(capsule)

    # 최근 N개 캡슐만 유지하고 싶을 때 쓰는 안전장치다.
    # None이면 제한하지 않는다.
    if max_capsules is not None and max_capsules >= 0:
        zero_state.previous_turn_capsules = zero_state.previous_turn_capsules[-max_capsules:]

    return zero_state


def set_current_turn_trace_ids(
    zero_state: ZeroState,
    trace_store: TraceStore,
    turn_id: str,
) -> ZeroState:
    """특정 turn_id의 trace ID 목록을 ZeroState.current_turn_trace_ids에 반영한다."""

    # 이번 턴의 실시간 trace 목록을 0번이 볼 수 있게 넣어준다.
    # 여기서도 요약하지 않고, 실제 존재하는 trace ID만 넣는다.
    zero_state.current_turn_trace_ids = [
        event.event_id for event in trace_store.events_for_turn(turn_id)
    ]
    return zero_state


def make_node_movement(
    *,
    movement_id: str,
    turn_id: str,
    step_index: int,
    node_id: str,
    node_type: str = "node",
    mode: str | None = None,
    input_trace_ids: list[str] | None = None,
    output_trace_ids: list[str] | None = None,
    input_data_ids: list[str] | None = None,
    output_data_ids: list[str] | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    status: str = "started",
) -> NodeMovement:
    """NodeMovement를 만들 때 리스트 기본값 실수를 피하기 위한 작은 helper."""

    return NodeMovement(
        movement_id=movement_id,
        turn_id=turn_id,
        step_index=step_index,
        node_id=node_id,
        node_type=node_type,
        mode=mode,
        input_trace_ids=input_trace_ids or [],
        output_trace_ids=output_trace_ids or [],
        input_data_ids=input_data_ids or [],
        output_data_ids=output_data_ids or [],
        started_at=started_at,
        finished_at=finished_at,
        status=status,
    )


def _first_event_id_by_type(
    trace_store: TraceStore,
    turn_id: str,
    event_type: str,
) -> str | None:
    """특정 턴에서 event_type이 처음으로 일치하는 trace ID를 찾는다."""

    for event in trace_store.events_for_turn(turn_id):
        if event.event_type == event_type:
            return event.event_id
    return None


def _last_event_id_by_type(
    trace_store: TraceStore,
    turn_id: str,
    event_type: str,
) -> str | None:
    """특정 턴에서 event_type이 마지막으로 일치하는 trace ID를 찾는다."""

    matched_event_id: str | None = None
    for event in trace_store.events_for_turn(turn_id):
        if event.event_type == event_type:
            matched_event_id = event.event_id
    return matched_event_id


def _validate_node_movements(turn_id: str, movements: list[NodeMovement]) -> None:
    """NodeMovement가 현재 턴 캡슐에 들어갈 수 있는 최소 조건을 확인한다."""

    seen_movement_ids: set[str] = set()
    for movement in movements:
        # 한 캡슐 안에서 movement_id가 중복되면 동선 추적이 흔들린다.
        if movement.movement_id in seen_movement_ids:
            raise ValueError(f"duplicate movement_id: {movement.movement_id}")
        seen_movement_ids.add(movement.movement_id)

        # 다른 턴의 동선을 섞으면 0번이 이전 턴을 잘못 읽게 된다.
        if movement.turn_id != turn_id:
            raise ValueError(
                f"NodeMovement.turn_id mismatch: expected {turn_id}, got {movement.turn_id}"
            )

        # step_index는 턴 안의 실행 순서이므로 음수면 안 된다.
        if movement.step_index < 0:
            raise ValueError(f"NodeMovement.step_index must be >= 0: {movement.step_index}")
