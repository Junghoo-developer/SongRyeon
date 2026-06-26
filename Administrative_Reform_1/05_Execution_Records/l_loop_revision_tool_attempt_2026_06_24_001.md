# L Loop Revision Tool Attempt 2026-06-24 001

## 목적

`L2:revision_query_frame:{attempt}`를 읽어 실제 문서 도구를 1회 실행하고, 그 결과를 trace/data에 기록할 수 있게 했다.

이번 구현은 아직 L3 재판정까지 가지 않는다.

현재 가능한 흐름:

```text
L2RevisionInputFrame
-> L2 revision query planner
-> L2 revision query frame
-> revision tool choice
-> revision tool result
-> revision tool distillation
-> revision tool budget
```

## 구현 파일

- `songryeon_core/loops/l_loop_revision_tool_attempt.py`
- `songryeon_core/runtime/smoke_test.py`
- `Administrative_Reform_1/04_Orders/ORDER_089_L_LOOP_CONTINUATION_V0.md`

## 새 함수

```text
run_l_loop_revision_tool_attempt(...)
```

이 함수는 다음을 수행한다.

1. `L2:revision_query_frame:{attempt}`를 읽는다.
2. query frame이 가리키는 도구를 확인한다.
3. tool catalog가 없으면 기록하고, 이미 있으면 재사용한다.
4. `tool_choice:L2_revision_{attempt}:{tool}`을 기록한다.
5. `search_docs` 또는 `read_artifact`를 실행한다.
6. tool result distillation을 기록한다.
7. 최신 `tool_use_budget`을 이어받아 새 budget frame을 기록한다.

## 저장되는 주요 record

예시:

```text
tool_choice:L2_revision_0001:search_docs
tool_result:search_docs:{trace_id}
tool_distillation:search_docs:{trace_id}
tool_budget:{turn_id}:{next_sequence}
```

## 예산 갱신 원칙

기존 최신 budget record가 있으면 그 숫자를 이어받는다.

예시:

```text
이전 tool_call_count = 1
revision 도구 실행 후 tool_call_count = 2

이전 query_count = 1
revision 도구 실행 후 query_count = 2
```

기존 cache status 목록도 가능하면 이어받고, 새 `search_docs` 실행의 cache status를 추가한다.

## 메타정보 경계

코드는 다음만 한다.

- query frame의 `target_tool_name` 확인
- 도구 실행
- 도구 결과 distillation
- budget 숫자 갱신
- 출처 trace/data 연결

코드는 다음을 하지 않는다.

- 검색 결과가 사용자 목표를 만족했는지 의미판정하지 않는다.
- 문서 내용의 사실성을 단정하지 않는다.
- L3의 partial/failed 사유를 해석해 성공 여부를 결정하지 않는다.

도구 실행 성공은 도구가 결과를 반환했다는 운영 상태일 뿐이고, 목표 달성 여부는 다음 L3 재판정 단계에서 다뤄야 한다.

## 아직 하지 않은 것

아직 다음 흐름은 연결하지 않았다.

```text
revision tool result/distillation/budget
-> L3 재판정
-> continuation decision 재평가
-> 필요 시 다음 attempt
```

또한 live `run_l_loop(...)` 내부에 이 경로를 아직 배선하지 않았다.

## 검증

```text
python -m compileall songryeon_core main.py dry_run.py
python main.py smoke-test
```

검증 결과:

```text
SMOKE_TEST_OK
l2_revision_tool_attempt_tool = search_docs
l2_revision_tool_attempt_budget = completed
```

