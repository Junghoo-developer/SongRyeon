# L Loop Return Reroute ID Scope - 2026-06-25-001

## 목적

`ORDER_094_L_LOOP_RETURN_REROUTE_ID_SCOPE_V0`에 따라, 같은 턴에서 L루프가 두 번 실행될 때 L 종료 후 0과 1이 주고받는 복귀/재진입 기록 ID가 충돌하지 않도록 run-scoped ID 규칙을 추가했다.

상위 L 재라우팅은 열지 않았다.

## 변경

- `LRunIds`에 L 바깥 복귀/재진입 ID 생성 규칙을 추가했다.
- `run_index=1`은 기존 legacy ID를 유지한다.
- `run_index>=2`는 legacy ID 앞에 `L:run:0002:` 실행 이름표를 붙인다.
- `record_l_loop_return_summary_for_node1()`이 선택적으로 `id_namespace`를 받아 return summary frame과 loop_return memory packet을 scoped ID로 기록할 수 있게 했다.
- `record_routing()`이 선택적으로 `id_namespace`를 받아 L 복귀 이후 route 결정을 scoped ID로 기록할 수 있게 했다.
- `run_dry_turn()`은 현재 1회차 L 실행에 legacy-compatible namespace를 전달한다. 따라서 기존 dry-run smoke ID는 유지된다.
- `Node2HandoffFrame`의 route path 판독은 scoped route ID도 읽을 수 있게 했다.
- `LLoopRunFrame.rerun_block_reason`은 남은 차단 사유를 node2 이후 하위 ID 계열로 갱신했다.

## scoped 가능해진 ID 계열

- `L:return_summary_frame`
- `memory_packet:node_1:loop_return_summary`
- `route:L`
- `route:2`

2회차 예:

```text
L:run:0002:L:return_summary_frame
L:run:0002:memory_packet:node_1:loop_return_summary
L:run:0002:route:L
L:run:0002:route:2
```

`LRunIds`에는 다음 downstream ID 생성 규칙도 추가했다.

```text
L:run:0002:node2_input:{turn_id}
L:run:0002:node_2:handoff_frame
L:run:0002:node_3:input_brief_frame
L:run:0002:report_dry_001
L:run:0002:node_4:gatekeeper_frame
L:run:0002:turn_outcome:{turn_id}
L:run:0002:boundary_dry_001
```

다만 이번 구현에서는 이 downstream 계열을 실제 런타임 기록 지점에 모두 적용하지 않았다.

## 아직 남은 고정 ID 계열

- `node2_input:{turn_id}`
- `node_2:handoff_frame`
- `node_3:input_brief_frame`
- `report_dry_001`
- `node_4:gatekeeper_frame`
- `turn_outcome:{turn_id}`
- `boundary_dry_001`

따라서 `same_turn_rerun_allowed=false`를 유지한다.

현재 차단 사유:

```text
CODE_STATUS:top_level_L_reroute_still_closed_until_node2_input_handoff_report_gatekeeper_and_turn_outcome_ids_are_run_scoped
```

다음 단계:

```text
CODE_TODO:scope_node2_input_handoff_node3_report_boundary_gatekeeper_and_turn_outcome_ids_before_top_level_L_reroute
```

## 검증

- `python -m compileall songryeon_core main.py` 통과.
- `python main.py smoke-test` 통과.

smoke-test는 다음을 추가로 확인한다.

- `run_index=1`은 기존 return summary, loop_return memory packet, route ID를 유지한다.
- `run_index=2`는 return summary와 loop_return memory packet에 scoped ID를 사용한다.
- `run_index=2`는 L 복귀 이후 route ID에 scoped ID를 사용한다.
- 같은 `DataStore` 안에 L 1회차와 2회차 복귀 기록을 함께 저장해도 ID 충돌이 없다.
- `same_turn_rerun_allowed=false`가 유지된다.
- `LLoopRunFrame.rerun_block_reason`이 남은 downstream ID 차단 사유를 말한다.
