# L Loop Downstream Reroute ID Scope - 2026-06-25

## Source Order

- `Administrative_Reform_1/04_Orders/ORDER_095_L_LOOP_DOWNSTREAM_REROUTE_ID_SCOPE_V0.md`

## Implemented Scope

`run_index=1`은 기존 downstream ID를 유지한다.

`run_index>=2`부터 다음 route=2 이후 downstream 기록 ID가 `L:run:0002:` scope를 사용한다.

- `turn_outcome:{turn_id}`
- `node2_input:{turn_id}`
- `node_2:handoff_frame`
- `boundary_dry_001`
- `node_3:input_brief_frame`
- `report_dry_001`
- `node_4:gatekeeper_frame`

`node_2:handoff_frame`, `node_3:input_brief_frame`, `node_4:gatekeeper_frame`는 실제 기록 함수에서 선택적 `id_namespace`를 받도록 연결했다.

`runtime/dry_run.py`의 route=2 downstream 배선은 현재 L 실행 namespace가 있으면 같은 namespace로 final memory packet, turn outcome, node2 input, handoff, boundary, node3 brief, report, gatekeeper를 기록한다.

`runtime/terminal_view.py`와 `runtime/dry_run.py`의 상태 조회는 legacy ID를 우선하되 없으면 `data_type` 기반 최신 record를 찾는 fallback을 갖는다.

## Runtime Honesty

상위 L 재라우팅은 열지 않았다.

- `same_turn_rerun_allowed=false`
- `rerun_block_reason=CODE_STATUS:top_level_L_reroute_still_closed_until_controller_policy_and_runtime_flow_are_explicitly_enabled`
- `planned_next_step=CODE_TODO:add_policy_guarded_same_turn_L_reroute_controller`

`LRunIds`의 2회차 namespace policy는 `run_scoped_l_internal_return_and_downstream_ids_v1`로 갱신했다.

## Remaining Fixed IDs

ORDER_095가 지정한 downstream 계열에는 남은 고정 ID가 없다.

다만 선택적 LLM boundary review record인 `node_2:boundary_review`는 이번 발주서의 지정 대상이 아니므로 legacy ID를 유지한다.

## Verification

```powershell
python -m compileall songryeon_core main.py
```

결과: 통과.

```powershell
python main.py smoke-test
```

결과: 통과. `SMOKE_TEST_OK`.

추가된 smoke는 같은 `DataStore` 안에서 L 1회차 legacy downstream 기록과 L 2회차 scoped downstream 기록이 충돌하지 않는지 확인한다.
