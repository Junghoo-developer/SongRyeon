# ORDER 096: Policy-Guarded Same-Turn L Reroute Controller v0

## 목적

`ORDER_094`와 `ORDER_095`에서 같은 턴의 L 1회차/2회차 기록 ID 충돌 방지 작업이 끝났다.

`ORDER_096`의 목표는 상위 L 재라우팅(`L3 => 0 => 1 => 0 => L`)을
무조건 여는 것이 아니라, 명시적 정책 guard 아래에서만 같은 턴 L 재진입을 허용하는
controller/runtime-flow v0를 만든다.

기본 실행은 계속 닫힌 상태를 유지한다.

## 배경

현재 `LLoopRunFrame`은 다음 상태를 말한다.

```text
same_turn_rerun_allowed=false
rerun_block_reason=CODE_STATUS:top_level_L_reroute_still_closed_until_controller_policy_and_runtime_flow_are_explicitly_enabled
planned_next_step=CODE_TODO:add_policy_guarded_same_turn_L_reroute_controller
```

이제 남은 문제는 ID 충돌이 아니라 정책과 흐름이다.

즉, 코드가 다음 질문에 답해야 한다.

- 어떤 조건에서 node_1의 두 번째 `route=L` 결정을 받아들일 수 있는가
- 같은 턴에서 L을 몇 번까지 다시 실행할 수 있는가
- 언제 반드시 `route=2`로 닫아 node_2/node_3/node_4 보고 경로로 보내야 하는가
- 이 결정을 의미 판단처럼 위장하지 않고 어떤 절대정보/혼합정보로 기록할 것인가

## 정책

1. 기본값은 닫힘이다.

다음과 같은 명시 guard가 켜지지 않으면 기존처럼 L 복귀 후 route=2로 닫는다.

```text
same_turn_l_reroute_enabled=false
max_l_runs_per_turn=1
```

2. 같은 턴 L 재라우팅은 명시 flag가 켜진 경우에만 허용한다.

v0 권장 형태:

```python
run_dry_turn(..., same_turn_l_reroute_enabled: bool = False, max_l_runs_per_turn: int = 1)
```

또는 동일한 의미의 runtime policy object를 둔다.

3. v0에서는 최대 2회차까지만 연다.

정책 flag가 켜져도 기본 실험 범위는 다음으로 제한한다.

```text
max_l_runs_per_turn=2
allowed_run_indexes=[1, 2]
```

3회차 이상은 이번 발주서 범위가 아니다.

4. node_1 route=L 결정을 코드가 새로 의미 판단하지 않는다.

코드는 다음 절대정보만 확인한다.

- policy flag가 켜졌는지
- 현재 L 실행 번호가 정책 상한보다 작은지
- `LRunIds`가 다음 run_index를 만들 수 있는지
- 직전 L 실행 record와 return summary/memory packet/route decision이 존재하는지
- DataStore ID 충돌 없이 다음 L 실행을 기록할 수 있는지

사용자 의도, 목표 달성 충분성, 의미적 재검색 필요성은 코드가 새로 판정하지 않는다.
LLM/node_1 또는 기존 L3/continuation frame이 만든 판단은 출처 달린 payload로만 읽는다.

5. route=2 닫힘은 항상 가능해야 한다.

정책 guard가 꺼져 있거나, 상한에 도달했거나, node_1이 `route=2`를 고르면
기존 route=2 downstream 보고 경로로 닫는다.

6. runtime record는 허용/차단 이유를 정직하게 말한다.

같은 턴 L 재실행이 허용된 run frame 또는 controller frame은 다음을 드러낸다.

```text
same_turn_rerun_allowed=true
rerun_block_reason=CODE_STATUS:none_policy_guard_enabled_for_same_turn_L_reroute
planned_next_step=CODE_STATUS:same_turn_L_reroute_runtime_flow_enabled
```

차단된 경우에는 구체 사유를 남긴다.

예:

```text
CODE_STATUS:same_turn_L_reroute_disabled_by_policy
CODE_STATUS:same_turn_L_reroute_max_runs_reached
CODE_STATUS:node1_selected_route_2
CODE_STATUS:missing_l_return_summary_for_reroute
```

## 구현 대상

우선 다음 파일을 조사하고 수정한다.

```text
runtime/dry_run.py
runtime/user_turn.py
runtime/terminal_view.py
runtime/smoke_test.py
loops/l_loop.py
loops/l_loop_namespace.py
nodes/node_0_memory_supplier.py
nodes/node_1_router.py
```

필요하면 별도 policy/controller 모듈을 추가할 수 있다.

예:

```text
runtime/same_turn_l_reroute.py
```

단, 새 모듈은 실제 중복을 줄일 때만 만든다.

## 구현 지침

1. `runtime/dry_run.py`의 강제 닫힘을 policy guard 아래로 옮긴다.

현재 구조는 L 복귀 뒤 다음 의도를 갖는다.

```text
MVP에서는 L 이후 재귀 루프를 아직 열지 않고 최종 보고로 닫는다.
```

이 흐름을 다음 형태로 바꾼다.

```text
if node_1 route=L and same_turn_l_reroute_enabled and run_index < max_l_runs_per_turn:
    run_l_loop(run_index=run_index + 1)
else:
    route=2 downstream으로 닫기
```

2. 2회차 L 실행은 반드시 `build_l_run_ids(run_index=2)` 계열을 사용한다.

다음 ID 계열이 모두 `L:run:0002:` scope를 유지해야 한다.

```text
L 내부 ID
L 복귀/route 재진입 ID
route=2 downstream ID
tool/result/distillation/budget/revision/continuation ID
```

3. route=2 downstream은 마지막 L 실행의 namespace로 닫는다.

같은 턴에서 L 2회차까지 실행했다면, 최종 보고 경로는 다음 계열을 사용한다.

```text
L:run:0002:turn_outcome:{turn_id}
L:run:0002:node2_input:{turn_id}
L:run:0002:node_2:handoff_frame
L:run:0002:boundary_dry_001
L:run:0002:node_3:input_brief_frame
L:run:0002:report_dry_001
L:run:0002:node_4:gatekeeper_frame
```

4. controller 판단을 별도 record로 남기는 것을 우선 검토한다.

예:

```text
L:reroute_controller:0001
L:run:0002:L:reroute_controller:0001
```

필드 예:

```text
controller_id
turn_id
current_run_index
next_run_index
same_turn_l_reroute_enabled
max_l_runs_per_turn
node1_route
controller_decision
decision_reason
source_trace_ids
source_data_ids
```

단, 기존 `LLoopRunFrame`만으로 충분히 표현 가능하면 새 schema는 최소화한다.

5. `user_turn` entrypoint에도 policy flag를 노출한다.

fake/qwen turn에서 기본값은 false다.
테스트나 수동 실험에서만 true로 넘길 수 있게 한다.

6. terminal view는 L 실행이 2회 이상일 때 이를 사람이 읽을 수 있게 표시한다.

단, node_3 최종 답변에는 내부 raw ID를 노출하지 않는다.

## Smoke-test 요구

다음 검사를 추가한다.

```text
기본 run_dry_turn은 same_turn_l_reroute_enabled=false이고 L은 1회만 실행됨
기본 run_dry_turn의 same_turn_rerun_allowed는 false 유지
기본 run_dry_turn의 rerun_block_reason은 policy disabled 또는 controller closed 사유를 말함

same_turn_l_reroute_enabled=true, max_l_runs_per_turn=2일 때 node_1 route=L이면 L 2회차가 실행됨
2회차 LRunIds namespace_policy는 run_scoped_l_internal_return_and_downstream_ids_v1
2회차 L 내부 주요 record가 L:run:0002:* 로 저장됨
2회차 L 복귀/route record가 L:run:0002:* 로 저장됨
2회차 route=2 downstream record가 L:run:0002:* 로 저장됨

같은 DataStore 안에서 1회차와 2회차 L 내부/복귀/downstream 기록이 충돌하지 않음
max_l_runs_per_turn=2이면 3회차 L은 실행되지 않음
상한 도달 뒤 route=2로 닫힘
node_3 final answer에는 내부 raw ID가 노출되지 않음
terminal_view는 2회차 L 실행과 최종 scoped downstream 상태를 빈 값 없이 표시함
```

가능하면 fake adapter를 사용해 node_1이 두 번째 복귀 시 `route=L`을 내는 결정적 smoke adapter를 추가한다.

## 금지

- 기본 실행에서 상위 L 재라우팅을 켜지 않는다.
- policy flag 없이 `same_turn_rerun_allowed=true`로 만들지 않는다.
- 3회차 이상 L 재실행을 이번 발주서에서 열지 않는다.
- 코드가 사용자 의도나 목표 충분성을 새로 의미 판단하지 않는다.
- LLM 의미 판단을 CODE 판정처럼 기록하지 않는다.
- `run_index=1`의 기존 ID와 smoke 기대값을 깨지 않는다.
- node_3 최종 답변에 내부 raw ID를 노출하지 않는다.
- 실패를 조용히 route=2 성공처럼 숨기지 않는다.
- `git add .` 같은 무차별 staging을 하지 않는다.

## 완료 조건

다음 명령이 통과해야 한다.

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

완료 보고에는 다음을 적는다.

- 기본 실행에서 상위 L 재라우팅이 닫혀 있는지 여부
- policy flag를 켰을 때 L 2회차가 실제 실행되는지 여부
- 2회차 L 내부/복귀/downstream ID가 모두 scoped인지 여부
- 3회차 이상이 차단되는지 여부
- `same_turn_rerun_allowed`, `rerun_block_reason`, `planned_next_step` 최종 값
- compileall / smoke-test 결과
