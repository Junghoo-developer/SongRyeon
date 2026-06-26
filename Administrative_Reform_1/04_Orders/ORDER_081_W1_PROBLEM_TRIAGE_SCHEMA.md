# ORDER 081: W1 Problem Triage Schema

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: W1이 "문제가 있냐 없냐"뿐 아니라 "그래서 뭐 어쩌라고"에 답해야 한다는 사용자 결정  
**목표**: W1이 문제감지, 손상위험, 해결가능성, 포기권고, 다음 경로 추천을 구조화해서 출력하게 한다.

## 배경

W1이 단순히 "문제 있음"만 출력하면 1은 다시 루프를 돌릴 수밖에 없다.  
그러면 W는 무한 루프 방지 장치가 아니라 새로운 루프 원인이 된다.

따라서 W1은 반드시 `so_what`과 `solvability`를 포함해야 한다.

## 스키마 초안

`W1ProblemTriageFrame`

필수 필드:

```text
frame_id: str
turn_id: str
user_question: str

problem_status:
  no_problem | problem_detected | unclear

blur_risk:
  low | medium | high

loop_damage_risk:
  none | possible | high

problem_type:
  none
  routing_unclear
  loop_authority_risk
  future_loop_dependency
  insufficient_context
  conflicting_signals
  user_intent_ambiguous
  current_structure_gap
  not_worth_expanding
  other

solvability:
  solvable_with_current_structure
  needs_more_info
  needs_new_loop_or_tool
  not_worth_solving_now
  unsolvable_in_current_turn

give_up_recommended: bool
give_up_reason: str

so_what: str

recommended_next_route:
  2 | L | R | ask_user | hold_for_definition | stop_safe_failure | W_retry

instruction_for_1: str
instruction_for_next_node: str

confidence:
  low | medium | high

source_trace_ids: list[str]
source_data_ids: list[str]
schema_name: W1ProblemTriageFrame
schema_version: 0.1
```

## 필드 의미

`problem_status`

- `no_problem`: 그냥 답해도 이후 루프가 망가지지 않는다.
- `problem_detected`: 대충 말하면 이후 루프/문서/권한 정의가 오염될 수 있다.
- `unclear`: W1도 판단을 못 끝냈다. 이 경우 무한 루프를 피해야 한다.

`blur_risk`

- 사용자가 한 말을 뭉뚱그려 처리했을 때 손상 가능성.

`loop_damage_risk`

- 현재 턴을 잘못 처리하면 이후 L/R/2/3 또는 문서화가 망가질 위험.

`solvability`

- 현재 구조만으로 풀 수 있는지, 사용자 질문이 필요한지, 새 루프/도구가 필요한지, 그냥 포기하는 게 나은지.

`give_up_recommended`

- W1이 "더 돌리지 말라"고 말할 수 있는 안전장치.

`so_what`

- W1 출력의 핵심 한 문장. 1이 이 문장만 읽어도 다음 행동을 이해해야 한다.

## 검증 규칙

1. `give_up_recommended=true`이면 `give_up_reason`은 비어 있으면 안 된다.
2. `problem_status=no_problem`이면 `recommended_next_route`는 보통 `2`여야 한다.
3. `solvability=needs_new_loop_or_tool`이면 `give_up_recommended`는 보통 true여야 한다.
4. `recommended_next_route=W_retry`는 같은 턴에서 최대 1회만 허용한다.
5. W1 LLM 출력은 상대/혼합 정보이며, 코드가 의미 판단 문장을 대신 쓰면 안 된다.

## 완료 기준

1. `schemas.py`에 `W1ProblemTriageFrame` dataclass와 validator가 추가된다.
2. validator가 enum과 필수 필드, give-up 조건을 검사한다.
3. smoke test에서 정상 frame과 실패 frame을 검증한다.
4. runtime 출력에서 W1의 `problem_status`, `solvability`, `so_what`, `recommended_next_route`가 보인다.
