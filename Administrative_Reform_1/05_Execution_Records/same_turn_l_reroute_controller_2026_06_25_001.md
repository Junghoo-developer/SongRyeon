# Same-Turn L Reroute Controller - 2026-06-25-001

## Source Order

- `Administrative_Reform_1/04_Orders/ORDER_096_POLICY_GUARDED_SAME_TURN_L_REROUTE_CONTROLLER_V0.md`

## Implemented Scope

`run_dry_turn()`에 명시 policy guard를 추가했다.

기본값은 닫힘이다.

```text
same_turn_l_reroute_enabled=false
max_l_runs_per_turn=1
```

실험 호출에서만 다음처럼 2회차 L 실행을 열 수 있다.

```text
same_turn_l_reroute_enabled=true
max_l_runs_per_turn=2
```

v0는 3회차 이상을 열지 않는다. `max_l_runs_per_turn`가 더 크게 들어와도 effective max는 2로 제한된다.

## Runtime Flow

L 복귀 뒤 node_1의 route 결정을 먼저 DataStore에 기록한다.

그 다음 `same_turn_l_reroute_controller`가 다음 절대정보만 확인한다.

- policy flag
- 현재 L 실행 번호와 effective max
- L return summary 존재 여부
- loop return memory packet 존재 여부
- node_1 return route record 존재 여부
- 다음 L run ID family의 DataStore 충돌 여부

controller는 사용자 의도나 목표 충분성을 새로 의미 판단하지 않는다.

## New/Updated Records

- `node_output:same_turn_l_reroute_controller_frame`
- `L:reroute_controller:0001`
- `L:run:0002:L:reroute_controller:0001`
- 1회차 L 복귀 route=L 충돌 회피 ID: `L:reroute:route:L`

2회차 L 실행이 허용된 경우 `LLoopRunFrame`은 다음을 기록한다.

```text
same_turn_rerun_allowed=true
rerun_block_reason=CODE_STATUS:none_policy_guard_enabled_for_same_turn_L_reroute
planned_next_step=CODE_STATUS:same_turn_L_reroute_runtime_flow_enabled
```

상한에 닿은 뒤에는 controller가 route=2 downstream으로 닫는다.

```text
decision_reason=CODE_STATUS:same_turn_L_reroute_max_runs_reached
planned_next_step=CODE_STATUS:route_2_downstream_close_after_same_turn_L_reroute_cap
```

## Entrypoints

- `run_dry_turn(..., same_turn_l_reroute_enabled=False, max_l_runs_per_turn=1)`
- `run_fake_user_turn(...)`
- `run_qwen_user_turn(...)`
- CLI:
  - `python main.py dry-run --same-turn-l-reroute --max-l-runs-per-turn 2`
  - `python main.py fake-turn ... --same-turn-l-reroute --max-l-runs-per-turn 2`
  - `python main.py qwen-turn ... --same-turn-l-reroute --max-l-runs-per-turn 2`

## Smoke Coverage

`python main.py smoke-test` now checks:

- default `run_dry_turn()` keeps same-turn reroute disabled
- default run executes L once
- policy-enabled fake adapter executes L run 2
- run 2 uses `run_scoped_l_internal_return_and_downstream_ids_v1`
- run 2 internal, return route, and route=2 downstream IDs are `L:run:0002:*`
- run 3 is not executed
- max close records `CODE_STATUS:same_turn_L_reroute_max_runs_reached`
- node_3 final answer does not expose `L:run:*` raw IDs
- terminal view shows run 2 and final scoped downstream state

## Verification

```powershell
python -m compileall songryeon_core main.py
```

Result: passed.

```powershell
python main.py smoke-test
```

Result: passed. `SMOKE_TEST_OK`.
