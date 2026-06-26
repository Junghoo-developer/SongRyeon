# Tool Efficiency Policy 2026-06-22 001

**대상 발주서**: `ORDER_049_TOOL_EFFICIENCY_POLICY.md`  
**성격**: 코드 구현 기록  
**결과**: dry-run과 smoke-test 통과

## 구현 요약

L루프의 도구 사용에 budget frame과 중복 방지 신호를 붙였다.  
이제 L루프는 search/read 도구를 실행할 때마다 현재 예산 상태, 실행한 query, 읽은 doc_id, cache_status, 입력 크기 추정값을 `ToolUseBudgetFrame`으로 남긴다.

## 코드 변경

1. `schemas.py`
   - `ToolCacheStatusRecord`를 추가했다.
   - `ToolUseBudgetFrame`을 추가했다.
   - `validate_tool_use_budget_frame()`을 추가했다.

2. `tool_efficiency_policy.py`
   - `record_tool_use_budget_frame()`을 추가했다.
   - `record_duplicate_tool_use_signal()`을 추가했다.
   - `cache_status_from_search_payload()`와 `make_cache_status_record()`를 추가했다.

3. `l_loop.py`
   - `max_query_candidates`, `max_read_doc_calls`, `max_input_chars`를 추가했다.
   - query 중복 실행 시 도구 호출 전에 중복 신호와 budget frame을 남기게 했다.
   - `search_docs` 결과의 `cache_status`를 budget frame에 기록하게 했다.
   - `max_tool_calls=1`처럼 read_doc budget이 없을 때는 read_doc을 생략하고 `max_tool_calls_reached`를 남긴다.
   - L3 입력과 L루프 output에 `tool_budget:*` data_id를 포함했다.

4. `dry_run.py`
   - dry-run에서 tool budget 관련 파라미터를 넘길 수 있게 했다.

5. `smoke_test.py`
   - hardcoded distillation trace 번호 의존을 제거하고 prefix 기반 검증으로 바꿨다.
   - 기본 budget frame과 cache_status 검증을 추가했다.
   - `max_tool_calls=1` budget 제한 케이스를 추가했다.
   - 중복 query 신호 기록 smoke를 추가했다.

## 검증

```text
python -m py_compile songryeon_core\core\schemas.py songryeon_core\tools\tool_efficiency_policy.py songryeon_core\loops\l_loop.py songryeon_core\runtime\dry_run.py songryeon_core\runtime\smoke_test.py
python main.py dry-run
python main.py smoke-test
```

smoke-test 핵심 결과:

```text
status=SMOKE_TEST_OK
trace_count=29
data_record_count=29
tool_budget_frame_count=5
tool_budget_cache_status=miss
tool_budget_limit_stop_reason=max_tool_calls_reached
duplicate_tool_signal=True
tool_distillation_count=2
l_loop_final_decision=stop_success
```

## 현재 한계

이번 구현은 규칙 기반 효율 정책이다.  
성과가 낮은 반복을 더 정교하게 판단하려면 검색 결과 점수 변화, query 후보 간 다양성, 읽은 문서의 재사용 가치를 함께 비교해야 한다. 이 부분은 후속 발주서나 `ORDER_050` 이후 replay/smoke 강화에서 다룰 수 있다.
