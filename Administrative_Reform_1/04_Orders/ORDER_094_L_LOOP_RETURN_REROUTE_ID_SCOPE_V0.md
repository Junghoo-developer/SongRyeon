# ORDER 094: L Loop Return Reroute ID Scope v0

## 목적

상위 L 재라우팅(`L3 => 0 => 1 => 0 => L`)을 열기 전에,
L루프가 끝난 뒤 0과 1이 주고받는 복귀/재진입 기록 ID를 run-scoped로 만든다.

`ORDER_094`의 목표는 상위 재라우팅을 실제로 여는 것이 아니다.
목표는 같은 턴에서 L루프 1회차와 2회차의 복귀 기록이 충돌하지 않게 만드는 것이다.

## 배경

이전 작업에서 L 내부 주요 ID는 `run_index>=2`부터 다음처럼 구분되었다.

```text
L:run:0002:L1:goal_frame
L:run:0002:L:control:0001
L:run:0002:tool_catalog:turn_dry_001
L:run:0002:tool_budget:turn_dry_001:0001
L:run:0002:L2:revision_query_frame:0001
L:run:0002:L3:revision_achievement:0001
```

하지만 L 바깥의 복귀/재진입 ID는 아직 고정이다.

```text
L:return_summary_frame
memory_packet:node_1:loop_return_summary
route:L
route:2
node2_input:{turn_id}
node_2:handoff_frame
node_3:input_brief_frame
```

이 상태에서 상위 L 재라우팅을 열면, 두 번째 L 실행 이후의 복귀 기록이
첫 번째 L 실행 이후의 복귀 기록과 섞이거나 DataStore ID 충돌을 일으킬 수 있다.

## 정책

1. `run_index=1`은 기존 ID를 유지한다.

```text
L:return_summary_frame
memory_packet:node_1:loop_return_summary
route:L
route:2
```

2. `run_index>=2`부터는 L 복귀/재진입 기록 ID에 run scope를 붙인다.

예:

```text
L:run:0002:L:return_summary_frame
L:run:0002:memory_packet:node_1:loop_return_summary
L:run:0002:route:L
L:run:0002:route:2
L:run:0002:node2_input:turn_dry_001
L:run:0002:node_2:handoff_frame
L:run:0002:node_3:input_brief_frame
```

3. ID scoping은 절대정보 처리다.

코드는 다음만 판단한다.

- 이 기록이 몇 번째 L 실행에 속하는지
- DataStore record가 존재하는지
- source_trace_ids/source_data_ids가 연결되는지
- schema 검증을 통과했는지

코드는 사용자 의도, 목표 달성, 의미적 충분성을 새로 판단하지 않는다.

4. 아직 상위 L 재라우팅을 실제로 열지 않는다.

이번 발주서가 끝나도 `same_turn_rerun_allowed`는 기본적으로 `false`를 유지한다.
단, `LLoopRunFrame.rerun_block_reason`은 이번 작업 후 남은 실제 차단 사유로 갱신한다.

## 구현 대상

우선 다음 함수와 ID 생성 지점을 조사하고 정리한다.

```text
node_0_memory_supplier.py
node_1_router.py
node_2_handoff.py
node_2_metainfo_boundary.py
node_3_reporter.py
node_4_gatekeeper.py
runtime/dry_run.py
runtime/user_turn.py
runtime/terminal_view.py
```

`LRunIds` 또는 별도 `LRunNamespace`에 다음 ID 생성 규칙을 추가한다.

```text
return_summary_frame_id
loop_return_memory_packet_id
route_decision_id
node2_input_frame_id
route2_handoff_frame_id
node3_input_brief_frame_id
node3_report_id
node4_gatekeeper_frame_id
turn_outcome_id
```

단, 한 번에 전체 런타임을 뒤엎지 않는다.
우선 L 복귀 경로에서 직접 충돌하는 ID부터 적용한다.

## 우선순위

1. 1순위

```text
L:return_summary_frame
memory_packet:node_1:loop_return_summary
route:{decision.route} 중 L 복귀 이후 route 기록
```

2. 2순위

```text
node2_input:{turn_id}
node_2:handoff_frame
node_3:input_brief_frame
```

3. 3순위

```text
report_dry_001
node_4:gatekeeper_frame
turn_outcome:{turn_id}
boundary_dry_001
```

## Runtime 정직성

아직 상위 재라우팅을 열 수 없으면 런타임 record가 그렇게 말해야 한다.

예:

```text
same_turn_rerun_allowed=false
rerun_block_reason=CODE_STATUS:...
planned_next_step=CODE_TODO:...
```

차단 사유가 줄어들면 기존 차단 사유를 그대로 두지 말고,
정확히 남은 ID 계열을 적는다.

## 금지

- 휴리스틱으로 사용자 의도를 맞히지 않는다.
- LLM 의미 판단을 코드 판정처럼 기록하지 않는다.
- `run_index=1`의 기존 smoke ID를 깨지 않는다.
- `git add .` 같은 무차별 staging을 하지 않는다.
- 상위 L 재라우팅을 실제로 켜지 않는다.

## Smoke-test 요구

다음 검사를 추가한다.

```text
run_index=1은 기존 복귀/route ID 유지
run_index=2는 L return summary와 loop_return memory packet이 scoped ID 사용
run_index=2는 L 복귀 이후 route ID가 scoped ID 사용
같은 DataStore 안에서 L 1회차와 2회차 복귀 기록이 충돌하지 않음
same_turn_rerun_allowed는 아직 false
LLoopRunFrame.rerun_block_reason은 남은 차단 사유를 정확히 말함
```

## 완료 조건

다음 명령이 통과해야 한다.

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

완료 보고에는 다음을 적는다.

- scoped 가능하게 바꾼 L 바깥 ID 계열
- 아직 남은 고정 ID 계열
- 상위 L 재라우팅을 열어도 되는지 여부
- compileall / smoke-test 결과
