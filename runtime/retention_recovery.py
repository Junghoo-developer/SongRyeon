"""Node2 직전에 전부 omit된 도구 원문 하나를 다시 공개한다."""

from pathlib import Path
from uuid import uuid4

from memory.audit import canonical_json
from memory.settings import DEFAULT_MEMORY_PATH
from memory.tool_records import (
    save_node1_all_omit_detection,
    save_node1_omit_recovery,
)
from nodes import Node1Action, RetentionDecision

from .state import (
    MAX_NODE1_TOOL_CALLS_PER_ROUND,
    OmittedToolCandidate,
    TurnState,
)


def should_recover_omitted_results(
    state,
    action,
    candidates,
    *,
    round_has_retained_content,
    total_tool_calls=0,
    maximum_total_tool_calls=None,
):
    """현재 행동이 Node2로 향할 때 전부 omit 복구가 필요한지 판정한다."""

    if not isinstance(state, TurnState):
        raise TypeError("state는 TurnState여야 합니다.")

    if not isinstance(action, Node1Action):
        raise TypeError("action은 Node1Action이어야 합니다.")

    if not isinstance(candidates, list):
        raise TypeError("candidates는 list여야 합니다.")

    if not isinstance(round_has_retained_content, bool):
        raise TypeError("round_has_retained_content는 bool이어야 합니다.")

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

    if any(
        not isinstance(candidate, OmittedToolCandidate)
        for candidate in candidates
    ):
        raise TypeError("모든 후보는 OmittedToolCandidate여야 합니다.")

    will_route_to_node2 = (
        action.action == "route_node2"
        or state.node1_tool_calls_in_round
        >= MAX_NODE1_TOOL_CALLS_PER_ROUND
        or (
            action.action == "use_tool"
            and maximum_total_tool_calls is not None
            and total_tool_calls >= maximum_total_tool_calls
        )
        or (
            action.action == "use_tool"
            and canonical_json(
                {
                    "arguments": action.arguments,
                    "tool_name": action.tool_name,
                }
            )
            in state.node1_tool_request_signatures
        )
    )
    return (
        will_route_to_node2
        and bool(candidates)
        and not round_has_retained_content
        and not state.node1_omit_recovery_used
    )


def begin_node1_omit_recovery(
    state,
    candidates,
    memory_path=DEFAULT_MEMORY_PATH,
):
    """감지 A를 먼저 저장한 뒤 이번 턴의 유일한 복구 기회를 연다."""

    if not isinstance(state, TurnState):
        raise TypeError("state는 TurnState여야 합니다.")

    if state.node1_omit_recovery_used:
        raise ValueError("이번 사용자 턴에는 omit 복구를 이미 사용했습니다.")

    if not isinstance(candidates, list) or not candidates:
        raise ValueError("omit 복구 후보가 하나 이상 필요합니다.")

    if any(
        not isinstance(candidate, OmittedToolCandidate)
        for candidate in candidates
    ):
        raise TypeError("모든 후보는 OmittedToolCandidate여야 합니다.")

    records = save_node1_all_omit_detection(
        round_number=state.node1_round,
        candidate_count=len(candidates),
        turn_id=f"{state.turn_id}-omit-detected-{uuid4()}",
        memory_path=memory_path,
    )
    state.node1_omit_recovery_used = True
    return records


def recover_node1_omitted_result(
    candidate,
    decision,
    candidate_number,
    memory_path=None,
):
    """선택 후보의 숨김 원문을 재검증하고 정확한 A 본문을 추가한다."""

    if not isinstance(candidate, OmittedToolCandidate):
        raise TypeError("candidate는 OmittedToolCandidate여야 합니다.")

    if not isinstance(decision, RetentionDecision):
        raise TypeError("decision은 RetentionDecision이어야 합니다.")

    observation = candidate.observation
    target_memory_path = (
        Path(observation.memory_path)
        if memory_path is None
        else Path(memory_path).resolve()
    )

    if target_memory_path != Path(observation.memory_path):
        raise ValueError(
            "도구 원문을 저장한 로그와 복구 본문을 저장할 로그가 다릅니다."
        )

    return save_node1_omit_recovery(
        decision=decision,
        candidate_number=candidate_number,
        source_information_id=observation.source_information_id,
        turn_id=observation.record_turn_id,
        memory_path=target_memory_path,
    )
