# ORDER 095: L Loop Downstream Reroute ID Scope v0

## 목적

상위 L 재라우팅(`L3 => 0 => 1 => 0 => L`)을 열기 전에,
`ORDER_094` 이후에도 남아 있는 node2 이후 downstream 기록 ID를 run-scoped로 만든다.

`ORDER_095`의 목표는 상위 재라우팅을 실제로 여는 것이 아니다.
목표는 같은 턴에서 L루프 1회차와 2회차가 각각 route=2 이후 경로까지 진행해도
`DataStore` 기록 ID가 충돌하지 않게 만드는 것이다.

## 배경

`ORDER_094`에서 L 복귀/재진입 직접 경로는 `run_index>=2`부터 scoped 가능해졌다.

```text
L:run:0002:L:return_summary_frame
L:run:0002:memory_packet:node_1:loop_return_summary
L:run:0002:route:L
L:run:0002:route:2
```

하지만 route=2 이후 downstream 기록은 아직 실제 런타임 기록 지점에서 고정 ID를 쓴다.

```text
node2_input:{turn_id}
node_2:handoff_frame
node_3:input_brief_frame
report_dry_001
node_4:gatekeeper_frame
turn_outcome:{turn_id}
boundary_dry_001
```

이 상태에서 상위 L 재라우팅을 열면, 두 번째 L 실행 뒤 route=2 경로가
첫 번째 route=2 경로의 node2/handoff/report/gatekeeper 기록과 충돌할 수 있다.

## 정책

1. `run_index=1`은 기존 ID를 유지한다.

```text
node2_input:{turn_id}
node_2:handoff_frame
node_3:input_brief_frame
report_dry_001
node_4:gatekeeper_frame
turn_outcome:{turn_id}
boundary_dry_001
```

2. `run_index>=2`부터는 downstream 기록 ID에 run scope를 붙인다.

예:

```text
L:run:0002:node2_input:turn_dry_001
L:run:0002:node_2:handoff_frame
L:run:0002:node_3:input_brief_frame
L:run:0002:report_dry_001
L:run:0002:node_4:gatekeeper_frame
L:run:0002:turn_outcome:turn_dry_001
L:run:0002:boundary_dry_001
```

3. ID scoping은 절대정보 처리다.

코드는 다음만 판단한다.

- 이 기록이 몇 번째 L 실행 이후 경로에 속하는지
- DataStore record가 존재하는지
- source_trace_ids/source_data_ids가 연결되는지
- schema 검증을 통과했는지

코드는 사용자 의도, 목표 달성, 의미적 충분성을 새로 판단하지 않는다.

4. 아직 상위 L 재라우팅을 실제로 열지 않는다.

이번 발주서가 끝나도 `same_turn_rerun_allowed`는 기본적으로 `false`를 유지한다.
단, 모든 downstream ID가 실제 기록 지점에서 scoped 적용되면
`LLoopRunFrame.rerun_block_reason`은 다음 실제 차단 사유로 갱신한다.

예:

```text
same_turn_rerun_allowed=false
rerun_block_reason=CODE_STATUS:top_level_L_reroute_still_closed_until_controller_policy_and_runtime_flow_are_explicitly_enabled
planned_next_step=CODE_TODO:add_policy_guarded_same_turn_L_reroute_controller
```

## 구현 대상

다음 파일에서 downstream ID 생성 지점과 record lookup 지점을 조사하고 정리한다.

```text
runtime/dry_run.py
runtime/user_turn.py
runtime/terminal_view.py
runtime/smoke_test.py
node_2_handoff.py
node_2_metainfo_boundary.py
node_3_reporter.py
node_4_gatekeeper.py
```

`LRunIds`에 이미 추가된 다음 ID 생성 규칙을 실제 기록 지점에 연결한다.

```text
node2_input_frame_id
route2_handoff_frame_id
node3_input_brief_frame_id
node3_report_id
node4_gatekeeper_frame_id
turn_outcome_id
metainfo_boundary_id
```

함수 인자는 가능하면 선택적 `id_namespace: LRunIds | None = None` 형태로 추가한다.
기본값이 `None`이면 기존 legacy ID를 그대로 사용한다.

## 우선순위

1. 1순위

```text
turn_outcome:{turn_id}
node2_input:{turn_id}
node_2:handoff_frame
boundary_dry_001
node_3:input_brief_frame
```

이 계열은 route=2 진입과 node_3 입력 경계의 핵심 record다.

2. 2순위

```text
report_dry_001
node_4:gatekeeper_frame
```

node_4 adapter가 없을 때도 `report_dry_001`은 항상 만들어질 수 있으므로 먼저 보장한다.
node_4는 adapter가 있을 때만 생성되지만, 생성될 경우 충돌하지 않아야 한다.

3. 3순위

```text
runtime/terminal_view.py의 lookup/fallback
runtime/user_turn.py의 include_data_records/pretty 경로
```

사람이 보는 출력이 scoped ID를 못 찾아서 빈 상태로 보이지 않게 한다.
단, 내부 raw ID를 사용자 최종 답변에 노출하지 않는 기존 원칙은 유지한다.

## 주의할 기존 의존성

다음 코드는 고정 ID 문자열을 직접 조회할 가능성이 높다.

```text
_read_payload_text(data_store, "node_2:handoff_frame", ...)
_read_payload_text(data_store, "node_3:input_brief_frame", ...)
_read_payload_text(data_store, "report_dry_001", ...)
_read_payload_text(data_store, "node_4:gatekeeper_frame", ...)
_payload(records, "node_2:handoff_frame")
_payload(records, "node_3:input_brief_frame")
_payload(records, "report_dry_001")
_payload(records, "node_4:gatekeeper_frame")
```

필요하면 record data_type 기반 lookup helper를 추가한다.
단, legacy ID를 삭제하거나 기존 1회차 smoke 기대값을 깨지 않는다.

## Runtime 정직성

이번 작업 후에도 상위 L 재라우팅을 열지 않는다면 런타임 record가 그렇게 말해야 한다.

남은 차단 사유를 기존 값으로 방치하지 않는다.

현재 차단 사유:

```text
CODE_STATUS:top_level_L_reroute_still_closed_until_node2_input_handoff_report_gatekeeper_and_turn_outcome_ids_are_run_scoped
```

이번 작업 완료 후 예상 차단 사유:

```text
CODE_STATUS:top_level_L_reroute_still_closed_until_controller_policy_and_runtime_flow_are_explicitly_enabled
```

다음 단계:

```text
CODE_TODO:add_policy_guarded_same_turn_L_reroute_controller
```

## 금지

- 상위 L 재라우팅을 실제로 켜지 않는다.
- `same_turn_rerun_allowed=true`로 바꾸지 않는다.
- 사용자 의도나 목표 충분성을 코드가 새로 판단하지 않는다.
- LLM 의미 판단을 코드 판정처럼 기록하지 않는다.
- `run_index=1`의 기존 smoke ID를 깨지 않는다.
- `git add .` 같은 무차별 staging을 하지 않는다.
- node_3 최종 답변에 내부 raw ID를 노출하지 않는다.

## Smoke-test 요구

다음 검사를 추가한다.

```text
run_index=1은 기존 downstream ID 유지
run_index=2는 turn_outcome ID가 scoped ID 사용
run_index=2는 node2_input frame ID가 scoped ID 사용
run_index=2는 route2 handoff frame ID가 scoped ID 사용
run_index=2는 boundary ID가 scoped ID 사용
run_index=2는 node3 input brief frame ID가 scoped ID 사용
run_index=2는 report ID가 scoped ID 사용
node_4 adapter가 있을 때 run_index=2 gatekeeper frame ID가 scoped ID 사용
같은 DataStore 안에서 L 1회차와 2회차 downstream 기록이 충돌하지 않음
Node2InputFrame.source_data_ids가 scoped route/return/L output ID를 빠뜨리지 않음
Node2HandoffFrame.source_data_ids가 scoped node2_input/final_memory_packet/turn_outcome ID를 빠뜨리지 않음
Node3InputBriefFrame.source_data_ids가 scoped handoff/boundary ID를 빠뜨리지 않음
same_turn_rerun_allowed는 아직 false
LLoopRunFrame.rerun_block_reason은 남은 controller/runtime-flow 차단 사유를 정확히 말함
```

## 완료 조건

다음 명령이 통과해야 한다.

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

완료 보고에는 다음을 적는다.

- 실제 기록 지점에 scoped 적용한 downstream ID 계열
- 아직 남은 고정 ID 계열이 있는지 여부
- 상위 L 재라우팅을 열어도 되는지 여부
- `same_turn_rerun_allowed`와 `rerun_block_reason`의 최종 값
- compileall / smoke-test 결과
