"""Node1 도구 실행과 짧은 원문·긴 원문 청크 보존 적용 흐름.

읽을 때 ``요청 → 실행 → 숨김 저장 → 선택 적용 → 라우팅``으로 나눈다.
Node1의 행동은 요청(R)이고, 허용 여부·실제 결과·실제 다음 노드는 코드가
적용한 사실(A)이다. 이 둘을 같은 값으로 취급하지 않는 것이 핵심이다.
"""

from pathlib import Path
from uuid import uuid4

from agent_tools import ToolResult
from memory.audit import canonical_json
from memory.gate_records import save_node1_route
from memory.settings import DEFAULT_MEMORY_PATH
from memory.tool_records import (
    save_node1_retention,
    save_tool_observation,
)
from nodes import Node1Action, RetentionDecision

from .state import (
    MAX_NODE1_TOOL_CALLS_PER_ROUND,
    NODE1,
    NODE2,
    RouteResolution,
    ToolObservation,
    TurnState,
)


class ToolCallLimitExceeded(RuntimeError):
    """Node1이 현재 라운드의 네 번째 도구를 요청했다."""


def _tool_request_signature(tool_name, arguments):
    """같은 도구와 논리적으로 같은 JSON 인자를 한 값으로 만든다."""

    return canonical_json(
        {
            "arguments": arguments,
            "tool_name": tool_name,
        }
    )


def execute_node1_tool(
    state,
    toolbox,
    tool_name,
    arguments,
    memory_path=DEFAULT_MEMORY_PATH,
):
    """도구 시도를 먼저 계산하고 실행 결과 원문을 숨김 저장한다."""

    if not isinstance(state, TurnState):
        raise TypeError("state는 TurnState여야 합니다.")

    if not callable(getattr(toolbox, "execute", None)):
        raise TypeError("toolbox에는 execute(tool_name, arguments)가 필요합니다.")

    if (
        state.node1_tool_calls_in_round
        >= MAX_NODE1_TOOL_CALLS_PER_ROUND
    ):
        raise ToolCallLimitExceeded(
            "Node1은 한 라운드에 도구를 최대 3회 사용할 수 있습니다."
        )

    # 모델의 의도가 아니라 실제 시도를 센다. 잘못된 도구 이름이나 실패한
    # 파일도 저장에 성공했다면 실행 예산을 소비한 1회다.
    attempt_number = state.node1_tool_calls_in_round + 1
    result = toolbox.execute(tool_name, arguments)

    if not isinstance(result, ToolResult):
        raise TypeError("toolbox.execute()는 ToolResult를 반환해야 합니다.")

    record_turn_id = f"{state.turn_id}-tool-{uuid4()}"

    records = save_tool_observation(
        tool_name=result.tool_name,
        arguments=result.arguments,
        success=result.success,
        content=result.content,
        error=result.error,
        source_node=NODE1,
        round_number=state.node1_round,
        attempt_number=attempt_number,
        maximum_attempts=MAX_NODE1_TOOL_CALLS_PER_ROUND,
        turn_id=record_turn_id,
        memory_path=memory_path,
    )
    state.node1_tool_request_signatures.add(
        _tool_request_signature(tool_name, arguments)
    )
    state.node1_tool_calls_in_round = attempt_number
    source_type = (
        "tool_raw_content"
        if result.success
        else "tool_raw_error"
    )
    source_record = next(
        record
        for record in records
        if record["information_type"] == source_type
    )

    return ToolObservation(
        record_turn_id=record_turn_id,
        source_information_id=source_record["information_id"],
        memory_path=str(Path(memory_path).resolve()),
        result=result,
        round_number=state.node1_round,
        attempt_number=attempt_number,
    )


def retain_node1_tool_result(
    observation,
    decision,
    memory_path=None,
):
    """Node1의 위치 결정을 검증하고 선택 본문을 코드로 정확히 복사한다."""

    if not isinstance(observation, ToolObservation):
        raise TypeError("observation은 ToolObservation이어야 합니다.")

    if not isinstance(decision, RetentionDecision):
        raise TypeError("decision은 RetentionDecision이어야 합니다.")

    target_memory_path = (
        Path(observation.memory_path)
        if memory_path is None
        else Path(memory_path).resolve()
    )

    if target_memory_path != Path(observation.memory_path):
        raise ValueError(
            "도구 원문을 저장한 로그와 선택 본문을 저장할 로그가 다릅니다."
        )

    selected_content, records = save_node1_retention(
        decision=decision,
        source_information_id=observation.source_information_id,
        turn_id=observation.record_turn_id,
        memory_path=target_memory_path,
    )

    return selected_content, records


def route_after_node1(
    state,
    action,
    memory_path=DEFAULT_MEMORY_PATH,
    *,
    total_tool_calls=0,
    maximum_total_tool_calls=None,
):
    """Node1 행동 요청과 라운드·턴 도구 상한을 기록·적용한다."""

    if not isinstance(state, TurnState):
        raise TypeError("state는 TurnState여야 합니다.")

    if not isinstance(action, Node1Action):
        raise TypeError("action은 Node1Action이어야 합니다.")

    if (
        not isinstance(total_tool_calls, int)
        or isinstance(total_tool_calls, bool)
        or total_tool_calls < 0
    ):
        raise ValueError("전체 도구 호출 수는 0 이상의 정수여야 합니다.")

    if maximum_total_tool_calls is not None and (
        not isinstance(maximum_total_tool_calls, int)
        or isinstance(maximum_total_tool_calls, bool)
        or maximum_total_tool_calls < 1
    ):
        raise ValueError("전체 도구 호출 상한은 1 이상의 정수여야 합니다.")

    reached_tool_limit = (
        state.node1_tool_calls_in_round
        >= MAX_NODE1_TOOL_CALLS_PER_ROUND
    )
    reached_total_tool_limit = (
        maximum_total_tool_calls is not None
        and total_tool_calls >= maximum_total_tool_calls
    )
    repeated_tool_request = (
        action.action == "use_tool"
        and _tool_request_signature(
            action.tool_name,
            action.arguments,
        )
        in state.node1_tool_request_signatures
    )

    # 모델의 route 요청은 그대로 적용할 수 있지만, 네 번째 도구 요청은
    # 모델이 원해도 코드가 막고 Node2로 보낸다.
    if action.action == "route_node2":
        resolution = RouteResolution(
            requested_action=action.action,
            next_node=NODE2,
            outcome="route_requested",
            forced_by_tool_limit=False,
        )
    elif reached_total_tool_limit:
        resolution = RouteResolution(
            requested_action=action.action,
            next_node=NODE2,
            outcome="tool_request_blocked_total_limit",
            forced_by_tool_limit=True,
        )
    elif reached_tool_limit:
        resolution = RouteResolution(
            requested_action=action.action,
            next_node=NODE2,
            outcome="tool_request_blocked_limit",
            forced_by_tool_limit=True,
        )
    elif repeated_tool_request:
        resolution = RouteResolution(
            requested_action=action.action,
            next_node=NODE2,
            outcome="tool_request_blocked_duplicate",
            forced_by_tool_limit=False,
        )
    else:
        resolution = RouteResolution(
            requested_action=action.action,
            next_node=NODE1,
            outcome="tool_request_allowed",
            forced_by_tool_limit=False,
        )

    save_node1_route(
        requested_action=action.action,
        reason=action.reason,
        tool_name=action.tool_name,
        arguments=action.arguments,
        next_node=resolution.next_node,
        outcome=resolution.outcome,
        forced_by_tool_limit=resolution.forced_by_tool_limit,
        turn_id=f"{state.turn_id}-node1-route-{uuid4()}",
        memory_path=memory_path,
    )
    return resolution
