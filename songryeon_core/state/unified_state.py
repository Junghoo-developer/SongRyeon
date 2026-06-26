from __future__ import annotations

from songryeon_core.core.schemas import SchemaBinding, UnifiedState
from songryeon_core.core.trace_store import TraceStore


def create_unified_state(turn_id: str, user_input: str) -> UnifiedState:
    """새 턴을 위한 UnifiedState를 만든다."""

    # UnifiedState는 0번을 제외한 일반 노드와 루프가 공유하는 현재 상황판이다.
    # 여기서는 판단이나 요약을 하지 않고, 턴 ID와 사용자 입력만 기본값으로 넣는다.
    _require_text("turn_id", turn_id)
    _require_text("user_input", user_input)
    return UnifiedState(turn_id=turn_id, user_input=user_input)


def add_trace_event_id(state: UnifiedState, event_id: str) -> UnifiedState:
    """UnifiedState에 trace ID 하나를 추가한다."""

    # trace ID는 이번 턴에서 벌어진 일의 절대정보 색인이다.
    # 같은 ID를 두 번 넣으면 흐름이 지저분해지므로 중복은 조용히 무시한다.
    _require_text("event_id", event_id)
    if event_id not in state.trace_event_ids:
        state.trace_event_ids.append(event_id)
    return state


def sync_trace_ids_from_store(
    state: UnifiedState,
    trace_store: TraceStore,
) -> UnifiedState:
    """TraceStore에 저장된 현재 턴 trace ID 목록을 UnifiedState에 반영한다."""

    # 이 함수는 TraceStore를 기준으로 현재 턴의 trace 목록을 다시 맞춘다.
    # 요약이나 중요도 판단 없이, 실제 존재하는 trace ID만 복사한다.
    state.trace_event_ids = [
        event.event_id for event in trace_store.events_for_turn(state.turn_id)
    ]
    return state


def set_current_route(state: UnifiedState, route: str | None) -> UnifiedState:
    """1번 라우터가 실제로 선택한 현재 route를 기록한다."""

    # route는 라우팅 이유가 아니라, 실제로 선택된 대상 이름이다.
    # 예: "2", "L". route를 비워야 할 때는 None을 쓴다.
    if route is not None:
        _require_text("route", route)
    state.current_route = route
    return state


def enter_loop(state: UnifiedState, loop_name: str) -> UnifiedState:
    """현재 실행 중인 루프 이름을 기록한다."""

    # 루프에 들어갔다는 사실만 기록한다.
    # 왜 들어갔는지는 상대정보이므로 라우터/노드 설계에서 따로 다룬다.
    _require_text("loop_name", loop_name)
    state.current_loop = loop_name
    return state


def exit_loop(state: UnifiedState, loop_name: str | None = None) -> UnifiedState:
    """현재 루프에서 빠져나왔음을 기록한다."""

    # loop_name을 넘기면 현재 루프와 일치하는지 확인한다.
    # 잘못된 루프를 종료하는 실수를 빨리 잡기 위한 안전장치다.
    if loop_name is not None and state.current_loop != loop_name:
        raise ValueError(
            f"current_loop mismatch: expected {loop_name}, got {state.current_loop}"
        )
    state.current_loop = None
    return state


def set_active_schema(
    state: UnifiedState,
    schema: SchemaBinding | None,
) -> UnifiedState:
    """현재 노드에 강제되는 스키마 정보를 기록한다."""

    # SchemaBinding은 "어떤 스키마가 걸렸는지"를 나타내는 절대정보다.
    # 스키마가 없는 상태로 되돌릴 때는 None을 넣는다.
    state.active_schema = schema
    return state


def set_metainfo_boundary_id(
    state: UnifiedState,
    boundary_id: str | None,
) -> UnifiedState:
    """2번 메타정보 경계관이 만든 결과 ID를 연결한다."""

    # boundary_id는 경계 내용 자체가 아니라, 그 결과물을 찾기 위한 이름표다.
    if boundary_id is not None:
        _require_text("boundary_id", boundary_id)
    state.metainfo_boundary_id = boundary_id
    return state


def set_latest_failure_signal_id(
    state: UnifiedState,
    failure_signal_id: str | None,
) -> UnifiedState:
    """가장 최근 실패/부족 신호 ID를 연결한다."""

    # 실패 이유나 복구 판단은 아직 넣지 않는다.
    # 지금은 실패 신호가 실제로 존재한다는 연결 정보만 다룬다.
    if failure_signal_id is not None:
        _require_text("failure_signal_id", failure_signal_id)
    state.latest_failure_signal_id = failure_signal_id
    return state


def _require_text(field_name: str, value: str) -> None:
    """비어 있으면 안 되는 문자열 필드를 검사한다."""

    if not value:
        raise ValueError(f"{field_name} must not be empty")
