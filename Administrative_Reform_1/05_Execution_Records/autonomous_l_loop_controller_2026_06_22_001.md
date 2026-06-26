# Autonomous L Loop Controller 2026-06-22 001

**대상 발주서**: `ORDER_047_AUTONOMOUS_L_LOOP_CONTROLLER.md`  
**성격**: 코드 구현 기록  
**결과**: dry-run과 smoke-test 통과

## 구현 요약

L루프가 `L1 -> L2 -> search_docs 1회 -> L3`로 고정되어 있던 흐름을 controller 기반 흐름으로 확장했다.

기본 dry-run의 L루프 동선은 다음과 같다.

```text
L1
-> tool catalog
-> L2
-> tool choice(search_docs)
-> LLoopControlFrame(continue_search)
-> search_docs
-> LLoopControlFrame(read_document)
-> read_doc
-> LLoopControlFrame(stop_success)
-> L3
```

## 코드 변경

1. `schemas.py`
   - `LLoopControlFrame`과 `validate_l_loop_control_frame()`을 추가했다.
   - controller decision은 `continue_search`, `read_document`, `stop_success`, `stop_failed`로 제한했다.
   - `L3AchievementFrame`이 `final_control_data_id`, `controller_decision`을 보존하게 했다.

2. `l_loop.py`
   - `max_iterations`, `max_tool_calls` budget을 추가했다.
   - search/read/stop 판단을 모두 `LLoopControlFrame`으로 DataStore에 저장하게 했다.
   - 검색 결과가 있으면 상위 문서를 `read_doc`으로 한 번 읽고 `stop_success`를 남긴다.
   - 검색 결과가 없거나 budget이 소진되면 `failure_signal`과 `stop_failed` control frame을 남기도록 했다.

3. `l3_result_keeper.py`
   - L3 achievement가 최종 controller 상태를 반영하게 했다.
   - `stop_success`와 검색 후보 존재가 함께 있을 때 `achieved`로 판단한다.

4. `smoke_test.py`
   - `L:control:0001`, `L:control:0002`, `L:control:0003` 검증을 추가했다.
   - `read_doc` 도구 사용 여부와 L3의 최종 controller 참조를 검증한다.

## 검증

```text
python -m py_compile songryeon_core\core\schemas.py songryeon_core\nodes\l3_result_keeper.py songryeon_core\loops\l_loop.py songryeon_core\runtime\smoke_test.py
python main.py dry-run
python main.py smoke-test
```

smoke-test 핵심 결과:

```text
status=SMOKE_TEST_OK
trace_count=22
data_record_count=22
l_loop_control_count=3
l_loop_final_decision=stop_success
l_loop_read_doc_used=True
llm_call_records=3
llm_retry_failure_type=parse_failed
l2_query_plan_candidates=2
l2_broken_planner_fallback=True
```

## 현재 한계

이번 구현은 controller의 구조와 budget 실행을 먼저 세운 단계다.  
검색 결과를 더 정교하게 증류하거나, 같은 query와 같은 doc 반복을 더 강하게 막는 정책은 `ORDER_048`, `ORDER_049`에서 이어서 다룬다.
