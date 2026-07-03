# Execution Record: ORDER 120 Tool Use Budget Query Count Diagnostic Implementation 2026-06-27 001

## 목적

`ToolUseBudgetFrame.query_count must not exceed max_query_attempts` 구조 실패의 실제 원인을 확인하고, 같은 예산 불일치가 다시 생길 때 어느 budget frame, route, L run, count에서 깨졌는지 드러나게 했다.

## 실제 원인

Qwen live 재현에서 강제 L route를 켰을 때 다음 진단이 확인됐다.

```text
budget_failure_type=query_count_exceeded_max_query_attempts
budget_failure_frame_id=tool_budget:turn_dry_001:0016
budget_failure_source_data_ids=[L2:revision_query_frame:0008, ...]
budget_failure_query_count=9
budget_failure_max_query_attempts=8
```

원인은 초기 search query가 아니라 L3 이후 continuation/revision 경로였다.

`record_l_loop_continuation_decision()`은 query 예산이 소진됐더라도 `read_doc` 예산과 unread candidate가 남아 있으면 `continue`를 허용할 수 있었다. 하지만 현재 구현된 continuation 행동은 unread candidate를 바로 `read_doc`하는 경로가 아니라 새 `L2 revision query`를 만든 뒤 tool attempt를 실행하는 경로뿐이다. 따라서 query 예산 8/8 상태에서도 revision query 0008이 추가 실행되며 `query_count=9`가 만들어졌다.

## 변경 요약

- `BudgetConsistencyError`를 추가해 `ToolUseBudgetFrame` 검증 실패에 구조화된 budget diagnostics를 붙였다.
- `record_tool_use_budget_frame()`이 validator 실패를 조용히 보정하지 않고, frame 값을 기반으로 budget failure field를 만들어 예외에 싣도록 했다.
- `run_qwen_user_turn()`의 `structure_failed` 진단이 `budget_diagnostics`를 top-level response에 병합하도록 했다.
- pretty runtime과 `structure_failed` fallback answer에 budget failure type/count/stage를 표시하도록 했다.
- L continuation 정책을 수정했다. 현재 read_doc 직행 continuation 경로가 없으므로 `remaining_query_attempts <= 0`이면 read_doc 예산이 남아 있어도 `stop_budget_exhausted`로 닫는다.

## 추가한 budget failure diagnostics 필드

- `budget_failure_type`
- `budget_failure_reason`
- `budget_failure_frame_id`
- `budget_failure_source_data_ids`
- `budget_failure_route`
- `budget_failure_l_run_id`
- `budget_failure_query_count`
- `budget_failure_max_query_attempts`
- `budget_failure_tool_calls`
- `budget_failure_max_tool_calls`
- `budget_failure_read_doc_count`
- `budget_failure_max_read_doc`
- `budget_failure_stage`

## 추가한 테스트

- `tests/test_order_120_tool_budget_diagnostics.py::test_tool_use_budget_validator_keeps_query_count_limit`
- `tests/test_order_120_tool_budget_diagnostics.py::test_valid_tool_use_budget_frame_records_successfully`
- `tests/test_order_120_tool_budget_diagnostics.py::test_budget_failure_diagnostics_expose_query_count_mismatch`
- `tests/test_order_120_tool_budget_diagnostics.py::test_structure_failed_renderer_includes_budget_failure_diagnostics`
- `tests/test_order_120_tool_budget_diagnostics.py::test_continuation_stops_when_query_budget_exhausted_even_with_unread_candidates`
- `tests/test_order_120_tool_budget_diagnostics.py::test_live_like_opinion_input_no_budget_query_count_structure_failure`

## 검증

```powershell
python -m pytest tests/test_order_120_tool_budget_diagnostics.py
```

결과: 6 passed in 11.69s.

```powershell
python -m compileall songryeon_core main.py
```

결과: 통과.

```powershell
python -m pytest
```

1차 결과: 424초 제한에서 timeout.

재실행 결과: 31 passed in 628.60s.

```powershell
python main.py smoke-test
```

1차 결과: 424초 제한에서 timeout.

재실행 결과: `SMOKE_TEST_OK`.

## live 확인

### 재현

다음 명령으로 budget failure 진단이 확인됐다.

```powershell
python main.py qwen-turn "지금 송련의 말하기 모드 설계가 너무 빡빡한지, 아니면 적절한지 의견을 말해줘. 단, 이건 네 해석이라는 점을 밝혀줘." --timeout 240 --pretty --force-l
```

결과:

```text
status=structure_failed
structure_failure_exception=BudgetConsistencyError
budget_failure_type=query_count_exceeded_max_query_attempts
budget_failure_query_count=9
budget_failure_max_query_attempts=8
budget_failure_source_data_ids includes L2:revision_query_frame:0008
```

### 사후 재검증

continuation 정책 수정 후 같은 live 명령과 축소 budget live 명령을 다시 시도했으나 Qwen 응답 시간이 길어져 각각 304초/244초 timeout으로 종료됐다. 따라서 post-fix Qwen force-L live 완료 여부는 이번 기록에서 확정하지 않는다.

비강제 live는 수정 전 한 차례 `status=ok`, `route=2`, `answer_basis=LLM:qwen3:14b`로 통과했지만, 수정 후 단독 재시도는 304초 timeout이었다.

## 유지한 것

- `ToolUseBudgetFrame` validator의 `query_count <= max_query_attempts`, `tool_call_count <= max_tool_calls`, `read_doc_count <= max_read_doc_calls` 조건은 유지했다.
- query_count를 max 값으로 조용히 덮어쓰지 않았다.
- router와 answer_basis mode 선택 정책은 건드리지 않았다.
- node_4 guard를 약화하지 않았다.
- W/R loop, scheduler, 외부 DB/vector DB/장기기억 DB를 건드리지 않았다.
- same-turn L reroute 횟수와 node_4 자동 재작성 루프를 늘리지 않았다.
