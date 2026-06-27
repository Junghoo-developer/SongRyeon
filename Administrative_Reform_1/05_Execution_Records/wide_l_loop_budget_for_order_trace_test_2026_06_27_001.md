# L loop 광폭 예산 테스트 설정 실행 기록

## 목적

ORDER 문서 추적 테스트에서 검색/열람 예산이 너무 작아 ORDER 목록을 충분히 못 읽는 문제를 현장 테스트용으로 완화했다.

## 변경

`songryeon_core/runtime/defaults.py`

- `DEFAULT_MAX_TOOL_CALLS`: 5 -> 18
- `DEFAULT_SEARCH_TOP_K`: 3 -> 12
- `DEFAULT_MAX_QUERY_ATTEMPTS`: 3 -> 8
- `DEFAULT_MAX_READ_DOC_CALLS`: 1 -> 10
- `DEFAULT_MAX_INPUT_CHARS`: 6000 -> 12000

`songryeon_core/loops/l_loop_budget.py`

- `SEARCH_TOP_K_CEILING`: 6 -> 12
- `MAX_TOOL_CALLS_CEILING`: 5 -> 18
- `MAX_READ_DOC_CALLS_CEILING`: 3 -> 10
- `MAX_QUERY_ATTEMPTS_CEILING`: 3 -> 8

`songryeon_core/runtime/smoke_test.py`

- 기본 예산 smoke가 하드코딩 숫자 대신 runtime default 상수를 보게 했다.
- 예산이 커져 L control/read_doc distillation record가 늘어나는 경우를 정상으로 보게 했다.
- budget consistency smoke는 일부러 좁은 `max_read_doc_calls=1` 조건을 넣어 read_doc/tool_call alignment 상황을 계속 검사하게 했다.

## 검증

```powershell
python -m compileall .\songryeon_core .\main.py
python .\main.py smoke-test
```

결과:

```text
compileall passed
SMOKE_TEST_OK
```

주요 확인값:

```text
l_loop_control_count=5
tool_distillation_count=4
l1_requirement_budget_read_doc=10
l1_requirement_budget_tool_calls=18
```

## 남은 주의

예산을 늘려도 L3가 `achieved`로 판단하면 L loop는 일찍 닫힐 수 있다.

따라서 ORDER ID 목록 전체 coverage를 보장하려면 다음 별도 MVP에서 명시 target coverage guard가 필요하다.
