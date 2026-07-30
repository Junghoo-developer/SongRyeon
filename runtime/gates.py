"""Node2·Node4의 permit/reject를 3회 제한과 라우팅에 적용한다."""

from uuid import uuid4

from memory.gate_records import save_gate_review
from memory.settings import DEFAULT_MEMORY_PATH
from nodes import ReviewDecision

from .state import (
    FINAL,
    MAX_REJECTIONS_PER_GATE,
    NODE1,
    NODE2,
    NODE3,
    NODE4,
    GateResolution,
    TurnState,
)


def _plan_gate_resolution(state, reviewer, decision):
    """상태를 바꾸기 전에 검토 결정의 적용 결과를 계산한다."""

    if reviewer == NODE2:
        current_rejections = state.node2_rejections
        retry_node = NODE1
        advance_node = NODE3
    elif reviewer == NODE4:
        current_rejections = state.node4_rejections
        retry_node = NODE3
        advance_node = FINAL
    else:
        raise ValueError("reviewer는 node2 또는 node4여야 합니다.")

    if decision.verdict == "permit":
        return GateResolution(
            reviewer=reviewer,
            next_node=advance_node,
            outcome="permit_applied",
            rejection_count=current_rejections,
            rejection_ignored=False,
        )

    if current_rejections < MAX_REJECTIONS_PER_GATE:
        return GateResolution(
            reviewer=reviewer,
            next_node=retry_node,
            outcome="reject_applied",
            rejection_count=current_rejections + 1,
            rejection_ignored=False,
        )

    return GateResolution(
        reviewer=reviewer,
        next_node=advance_node,
        outcome="reject_ignored_limit",
        rejection_count=current_rejections,
        rejection_ignored=True,
    )


def apply_gate_decision(
    state,
    reviewer,
    decision,
    memory_path=DEFAULT_MEMORY_PATH,
):
    """Node2·Node4의 결정을 기록하고 3회 반려 규칙을 상태에 적용한다."""

    if not isinstance(state, TurnState):
        raise TypeError("state는 TurnState여야 합니다.")

    if not isinstance(decision, ReviewDecision):
        raise TypeError("decision은 ReviewDecision이어야 합니다.")

    resolution = _plan_gate_resolution(state, reviewer, decision)
    record_turn_id = f"{state.turn_id}-{reviewer}-{uuid4()}"

    # 로그 저장이 실패하면 아래 상태 변경도 실행하지 않는다.
    save_gate_review(
        reviewer=reviewer,
        verdict=decision.verdict,
        reason=decision.reason,
        rejection_count=resolution.rejection_count,
        maximum_rejections=MAX_REJECTIONS_PER_GATE,
        outcome=resolution.outcome,
        next_node=resolution.next_node,
        rejection_ignored=resolution.rejection_ignored,
        turn_id=record_turn_id,
        memory_path=memory_path,
    )

    if reviewer == NODE2:
        state.node2_rejections = resolution.rejection_count
        if resolution.rejection_ignored:
            state.node2_limit_exhausted = True

        if resolution.outcome == "reject_applied":
            state.node1_round += 1
            state.node1_tool_calls_in_round = 0
    else:
        state.node4_rejections = resolution.rejection_count
        if resolution.rejection_ignored:
            state.node4_limit_exhausted = True

    return resolution
