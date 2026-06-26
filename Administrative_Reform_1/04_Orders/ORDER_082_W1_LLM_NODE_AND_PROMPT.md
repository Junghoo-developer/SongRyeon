# ORDER 082: W1 LLM Node And Prompt

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: W1은 문제감지와 "그래서 무엇을 하라"를 LLM 판단으로 작성해야 한다는 설계  
**목표**: W1 LLM 노드와 프롬프트를 추가하고, W1이 구조화된 triage frame만 출력하게 한다.

## 배경

W1의 핵심 판단은 코드가 쓰기 어렵다.

예를 들어 "이 턴을 대충 말하면 이후 L루프가 망가지는가"는 단순 키워드가 아니라 대화/설계 맥락 판단이다.  
따라서 W1은 LLM 노드로 구현한다.

단, W1은 권한이 작아야 한다.  
W1은 판단 보조 보고서를 쓸 뿐, 라우팅과 답변을 직접 실행하지 않는다.

## 구현 범위

1. `songryeon_core/nodes/w1_problem_triage.py` 추가.
2. `songryeon_core/prompts/w1_problem_triage_v0.md` 추가.
3. `LLMNodeExecutor`를 사용해 W1 호출을 기록한다.
4. W1 출력은 `W1ProblemTriageFrame` validator를 통과해야 한다.
5. 실패 시 안전 fallback을 제공하되, fallback은 의미 판단인 척하면 안 된다.

## W1 입력

W1은 다음을 본다.

```text
user_question
recent_runtime_summary
node_0_memory_packet_for_W
current_route_context
available_routes
latest_l_loop_summary_if_any
latest_route2_handoff_if_any
node4_gate_status_if_any
```

W1에게 직접 주면 안 되는 것:

```text
full DataStore raw dump
full trace raw dump
tool credentials
private file paths unless already allowed
node_3 answer draft as final truth
```

## W1 프롬프트 원칙

프롬프트는 다음을 명시한다.

1. 너는 최종 라우터가 아니다.
2. 너는 도구를 쓰지 않는다.
3. 너는 최종 답변을 쓰지 않는다.
4. 너는 문제 유무, 손상 위험, 해결 가능성, 포기 권고를 판단한다.
5. `so_what`은 반드시 1이 바로 행동할 수 있는 문장이어야 한다.
6. 현재 구조로 해결 불가능하면 과감히 포기/보류/질문을 추천한다.
7. 애매하면 무한 루프보다 ask_user/hold/stop을 우선한다.

## Fallback 원칙

W1 LLM 호출 실패 시 code fallback은 다음처럼 정직해야 한다.

```text
problem_status: unclear
blur_risk: medium
loop_damage_risk: possible
solvability: needs_more_info
give_up_recommended: false
so_what: CODE_STATUS:w1_llm_unavailable
recommended_next_route: ask_user
instruction_for_1: W1 LLM 판단 실패. 사용자에게 한 가지 확인 질문을 하거나 안전하게 보류하라.
```

코드 fallback은 자연어 의미판단을 꾸며내면 안 된다.

## 완료 기준

1. W1 프롬프트 파일이 추가된다.
2. W1 노드 함수가 fake adapter와 Qwen adapter 양쪽에서 작동한다.
3. W1 LLM call record가 남는다.
4. W1 출력이 스키마를 통과한다.
5. W1 실패 시 code fallback이 `CODE_STATUS`를 노출한다.
