"""사용자 입력 하나를 네 노드와 실제 모델로 끝까지 처리하는 데모 루프.

이 파일은 마지막에 읽는 조립 설명서다. 세부 규칙을 직접 구현하지 않고
``memory``·``tool_flow``·``gates``·``NodeCaller``를 순서대로 호출한다.
처음에는 ``current_node``가 어디서 바뀌는지만 따라가고, 각 함수 내부는
해당 모듈에서 따로 읽는 편이 쉽다.
"""

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from memory.conversation_records import (
    save_final_delivery,
    save_node3_answer,
    save_user_input,
)
from memory.agent_view import (
    freeze_agent_memory_floor,
    load_turn_memory_context,
)

from .gates import apply_gate_decision
from .node_calls import NodeCaller
from .retention_recovery import (
    begin_node1_omit_recovery,
    recover_node1_omitted_result,
    should_recover_omitted_results,
)
from .state import (
    FINAL,
    NODE1,
    NODE2,
    NODE3,
    NODE4,
    OmittedToolCandidate,
    create_turn_state,
)
from .tool_flow import (
    execute_node1_tool,
    retain_node1_tool_result,
    route_after_node1,
)

@dataclass(frozen=True)
class DemoTurnResult:
    """완료된 데모 한 턴에서 사용자와 CLI가 확인할 결과."""

    turn_id: str
    answer: str
    total_tool_calls: int
    node1_rounds: int
    node2_rejections: int
    node3_drafts: int
    node4_rejections: int
    node2_limit_exhausted: bool
    node4_limit_exhausted: bool
    last_node4_reject_reason: str | None
    final_outcome: str


def _emit(on_event, node_name, message):
    """CLI 진행 표시를 core 로직의 print와 분리한다."""

    if on_event is not None:
        on_event(node_name, message)


def run_demo_turn(
    user_input,
    *,
    client,
    toolbox,
    memory_path,
    on_event=None,
    maximum_total_tool_calls=None,
):
    """사용자 입력을 Node1→2→3→4로 처리해 답변을 반환한다.

    ``client``, ``toolbox``, ``memory_path``를 반드시 주입하게 해 테스트가
    실제 모델이나 실제 기억을 우연히 사용하지 못하도록 한다.
    """

    if not isinstance(user_input, str) or not user_input.strip():
        raise ValueError("사용자 입력은 비어 있지 않은 문자열이어야 합니다.")

    if not callable(getattr(toolbox, "execute", None)):
        raise TypeError("toolbox에는 execute(tool_name, arguments)가 필요합니다.")

    if maximum_total_tool_calls is not None and (
        not isinstance(maximum_total_tool_calls, int)
        or isinstance(maximum_total_tool_calls, bool)
        or maximum_total_tool_calls < 1
    ):
        raise ValueError("전체 도구 호출 상한은 1 이상의 정수여야 합니다.")

    # 1단계: 새 턴을 만들고 사용자 발화의 출처 A와 내용 R을 먼저 기록한다.
    memory_path = Path(memory_path).resolve()
    state = create_turn_state()
    user_input_records = save_user_input(
        user_input=user_input,
        turn_id=state.turn_id,
        memory_path=memory_path,
    )
    turn_memory_context = load_turn_memory_context(
        user_input_records[0]["information_id"],
        memory_path,
    )
    # 2단계: 이번 턴의 기억 하한선을 한 번만 고정한다. 이후 로그가 늘어도
    # 모든 노드는 이 기준점부터 같은 공개 기록을 다시 읽는다.
    memory_floor = freeze_agent_memory_floor(memory_path)
    node_caller = NodeCaller(
        client=client,
        user_input=user_input,
        turn_id=state.turn_id,
        memory_path=memory_path,
        memory_floor=memory_floor,
        turn_memory_context=turn_memory_context,
    )

    current_node = NODE1
    total_tool_calls = 0
    node3_drafts = 0
    latest_answer = None
    latest_answer_information_id = None
    last_node4_reject_reason = None
    final_outcome = ""

    # 3단계: 모델은 행동·판정을 요청하고, Python 코드가 실제 다음 노드를
    # 결정한다. 어떤 노드도 이 while 조건이나 카운터를 직접 바꿀 수 없다.
    while current_node != FINAL:
        if current_node == NODE1:
            omitted_candidates = []
            round_has_retained_content = False
            _emit(
                on_event,
                NODE1,
                f"{state.node1_round}라운드에서 다음 행동을 판단합니다.",
            )
            action = node_caller.ask_node1_action()

            # 한 Node1 라운드 안에서 도구 사용과 결과 보존을 최대 3회 반복한다.
            while True:
                if should_recover_omitted_results(
                    state,
                    action,
                    omitted_candidates,
                    round_has_retained_content=(
                        round_has_retained_content
                    ),
                    total_tool_calls=total_tool_calls,
                    maximum_total_tool_calls=maximum_total_tool_calls,
                ):
                    begin_node1_omit_recovery(
                        state,
                        omitted_candidates,
                        memory_path=memory_path,
                    )
                    _emit(
                        on_event,
                        NODE1,
                        "모든 원문이 생략돼 최종 보존 대상을 다시 고릅니다.",
                    )
                    recovery_choice = (
                        node_caller.ask_node1_recovery_choice(
                            omitted_candidates
                        )
                    )
                    candidate_number = (
                        recovery_choice.candidate_number
                    )
                    candidate = omitted_candidates[
                        candidate_number - 1
                    ]
                    recovery_decision = (
                        node_caller.ask_node1_recovery_retention(
                            candidate,
                            candidate_number,
                        )
                    )
                    recovered_content, _ = (
                        recover_node1_omitted_result(
                            candidate,
                            recovery_decision,
                            candidate_number,
                            memory_path=memory_path,
                        )
                    )
                    round_has_retained_content = True
                    _emit(
                        on_event,
                        NODE1,
                        "최종 보존 완료: "
                        + f"본문 {len(recovered_content)}자 복구",
                    )

                route = route_after_node1(
                    state,
                    action,
                    memory_path=memory_path,
                    total_tool_calls=total_tool_calls,
                    maximum_total_tool_calls=maximum_total_tool_calls,
                )

                if route.next_node == NODE2:
                    _emit(
                        on_event,
                        NODE1,
                        "증거 수집을 마치고 Node2로 이동합니다.",
                    )
                    current_node = NODE2
                    break

                _emit(
                    on_event,
                    NODE1,
                    f"도구를 실행합니다: {action.tool_name}",
                )
                observation = execute_node1_tool(
                    state,
                    toolbox,
                    action.tool_name,
                    action.arguments,
                    memory_path=memory_path,
                )
                total_tool_calls += 1
                tool_decision = node_caller.ask_node1_after_tool(
                    observation
                )
                retained_content, _ = retain_node1_tool_result(
                    observation,
                    tool_decision.retention,
                    memory_path=memory_path,
                )
                if (
                    retained_content is None
                    and observation.result.success
                ):
                    omitted_candidates.append(
                        OmittedToolCandidate(
                            observation=observation,
                            review=tool_decision.retention.review,
                        )
                    )
                elif retained_content is not None:
                    round_has_retained_content = True

                retained_label = (
                    "본문을 남기지 않음"
                    if retained_content is None
                    else f"본문 {len(retained_content)}자 보존"
                )
                _emit(
                    on_event,
                    NODE1,
                    f"도구 검토 완료: {retained_label}",
                )
                action = tool_decision.next_action

        elif current_node == NODE2:
            # Node2의 판정 자체는 R이고 apply_gate_decision의 적용 결과가 A다.
            _emit(on_event, NODE2, "증거가 충분한지 검토합니다.")
            decision = node_caller.ask_node2_review()
            resolution = apply_gate_decision(
                state,
                NODE2,
                decision,
                memory_path=memory_path,
            )
            _emit(
                on_event,
                NODE2,
                f"{decision.verdict}: {decision.reason}",
            )
            current_node = resolution.next_node

        elif current_node == NODE3:
            # 답변 내용은 R로 저장한다. 아직 Node4를 통과하지 않은 초안이다.
            _emit(on_event, NODE3, "사용자 답변을 작성합니다.")
            answer = node_caller.ask_node3_answer()
            answer_turn_id = f"{state.turn_id}-node3-{uuid4()}"
            answer_records = save_node3_answer(
                answer=answer.answer,
                turn_id=answer_turn_id,
                memory_path=memory_path,
            )
            answer_record = next(
                record
                for record in answer_records
                if record["information_type"] == "node3_answer"
            )
            latest_answer = answer.answer
            latest_answer_information_id = answer_record["information_id"]
            node3_drafts += 1
            current_node = NODE4

        elif current_node == NODE4:
            # Node4가 permit하거나 한도가 소진되어 FINAL로 갈 때만 런타임이
            # 어느 Node3 답변을 사용자에게 보냈는지 A 링크로 남긴다.
            _emit(on_event, NODE4, "답변이 A를 왜곡했는지 검열합니다.")
            decision = node_caller.ask_node4_review(latest_answer)
            resolution = apply_gate_decision(
                state,
                NODE4,
                decision,
                memory_path=memory_path,
            )
            _emit(
                on_event,
                NODE4,
                f"{decision.verdict}: {decision.reason}",
            )
            if decision.verdict == "reject":
                last_node4_reject_reason = decision.reason
            else:
                last_node4_reject_reason = None
            current_node = resolution.next_node

            if current_node == FINAL:
                final_outcome = resolution.outcome
                save_final_delivery(
                    answer_information_id=latest_answer_information_id,
                    turn_id=f"{state.turn_id}-final-{uuid4()}",
                    memory_path=memory_path,
                )

        else:
            raise RuntimeError(f"알 수 없는 runtime 노드입니다: {current_node}")

    return DemoTurnResult(
        turn_id=state.turn_id,
        answer=latest_answer,
        total_tool_calls=total_tool_calls,
        node1_rounds=state.node1_round,
        node2_rejections=state.node2_rejections,
        node3_drafts=node3_drafts,
        node4_rejections=state.node4_rejections,
        node2_limit_exhausted=state.node2_limit_exhausted,
        node4_limit_exhausted=state.node4_limit_exhausted,
        last_node4_reject_reason=last_node4_reject_reason,
        final_outcome=final_outcome,
    )
