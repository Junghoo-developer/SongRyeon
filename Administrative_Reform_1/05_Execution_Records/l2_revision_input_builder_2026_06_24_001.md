# L2 Revision Input Builder 2026-06-24 001

## 목적

ORDER 089의 다음 단계로, L2가 재검색 계획을 세우기 전에 받을 입력 묶음인 `L2RevisionInputFrame`을 실제 DataStore record로 만들 수 있게 했다.

이번 구현은 L2 재검색을 실행하지 않는다.

목표는 다음 실행 전에 입력 데이터의 경계를 먼저 고정하는 것이다.

```text
L3 partial/failed
-> LLoopContinuationFrame
-> 0(l3_continuation_summary_for_L2)
-> L2RevisionInputFrame
```

## 구현 파일

- `songryeon_core/nodes/l2_revision_input.py`
- `songryeon_core/runtime/smoke_test.py`
- `Administrative_Reform_1/04_Orders/ORDER_089_L_LOOP_CONTINUATION_V0.md`

## 새 함수

```text
record_l2_revision_input_frame(...)
```

이 함수는 다음 record를 읽는다.

- `L1:goal_frame`
- `L2:query_frame`
- `L3:achievement_frame`
- `L:continuation:{attempt}`
- `memory_packet:L2:l3_continuation_summary_for_L2:{attempt}`
- 최신 `tool_use_budget`

그리고 다음 record를 만든다.

```text
L2:revision_input:{attempt}
```

data type:

```text
node_input:L2_revision_input_frame
```

## 들어가는 주요 값

`L2RevisionInputFrame`에는 다음 값이 들어간다.

- L1 거시 목표
- L1 미시 목표
- 이전 L2 검색어
- 직전 도구 이름
- 이미 읽은 문서 이름 또는 문서 식별 경로
- 아직 읽지 않은 후보 요약
- L3 목표 달성 상태
- L3 goal match 상태
- L3 semantic goal match 상태
- L3 feedback text
- 남은 tool call 수
- 남은 query 시도 수
- 남은 read_doc call 수
- source trace/data IDs

## 메타정보 경계

이번 구현은 L3 reason이나 문서 preview의 의미를 코드가 해석하지 않는다.

코드가 하는 일은 다음뿐이다.

```text
구조화 record에서 값 읽기
값 복사하기
예산 숫자 계산하기
출처 연결하기
스키마 검증하기
```

따라서 `L2RevisionInputFrame`은 L2가 다음 판단을 하기 위한 입력이지, 코드가 "무엇을 검색해야 한다"고 의미판단한 결과가 아니다.

## 아직 하지 않은 것

아직 L2 revision query planner를 실행하지 않았다.

즉, live runtime에서 다음 흐름은 아직 미구현이다.

```text
L2RevisionInputFrame
-> L2 revision_query_plan
-> tools
-> L3 재판정
```

다음 단계는 L2가 `initial_query_plan`과 `revision_query_plan`을 구분해서 프롬프트와 입력 payload를 받게 만드는 것이다.

## 검증

```text
python -m compileall songryeon_core main.py dry_run.py
python main.py smoke-test
```

검증 결과:

```text
SMOKE_TEST_OK
l_loop_continuation_continue = continue
l3_continuation_memory_mode = l3_continuation_summary_for_L2
l2_revision_input_attempt = 1
l2_revision_input_previous_tool = search_docs
```

