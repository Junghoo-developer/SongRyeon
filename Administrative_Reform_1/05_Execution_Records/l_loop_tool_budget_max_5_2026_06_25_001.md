# L Loop Tool Budget Max 5 - 2026-06-25-001

## Source Order

- `Administrative_Reform_1/04_Orders/ORDER_097_L_LOOP_TOOL_BUDGET_MAX_5_V0.md`

## 변경

L루프 도구 호출 예산을 5회 기준으로 맞췄다.

- `DEFAULT_MAX_TOOL_CALLS = 5`
- `MAX_TOOL_CALLS_CEILING = 5`
- `run_l_loop(..., max_tool_calls=5)`
- smoke-test 기본 예산 기대값 5로 갱신

## 범위 밖

이번 작업은 같은 턴 L 재진입 횟수를 바꾸지 않았다.

`same_turn_l_reroute`는 여전히 `ORDER_096`의 v0 정책을 따른다.

## 검증

```powershell
python -m compileall songryeon_core main.py
```

결과: 통과.

```powershell
python main.py smoke-test
```

결과: 통과. `SMOKE_TEST_OK`.

추가 확인:

```text
first_budget_max_tool_calls = 5
approved_max_tool_calls = 5
max_tool_calls_ceiling = 5
```
