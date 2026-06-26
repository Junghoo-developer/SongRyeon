# L2 Revision Query Frame 2026-06-24 001

## 목적

`L2:revision_query_plan:{attempt}`에서 선택된 후보를 실제 도구 실행 직전의 `L2QueryFrame`으로 확정했다.

이번 구현은 아직 도구를 실행하지 않는다.

현재 흐름은 다음까지 가능하다.

```text
L2RevisionInputFrame
-> L2 revision query planner
-> L2:revision_query_plan:{attempt}
-> L2:revision_query_frame:{attempt}
```

## 구현 파일

- `songryeon_core/core/schemas.py`
- `songryeon_core/nodes/l2_query_setter.py`
- `songryeon_core/runtime/smoke_test.py`
- `Administrative_Reform_1/04_Orders/ORDER_089_L_LOOP_CONTINUATION_V0.md`

## 추가된 query source

`L2QueryFrame.query_source` 후보에 다음 값을 추가했다.

```text
revision_llm_query_plan
revision_fallback_query_plan
```

기존 `llm_query_plan`과 구분하는 이유는 초기 L2 검색어와 재시도 L2 검색어가 같은 스키마를 쓰더라도 운영 의미가 다르기 때문이다.

## 새 함수

```text
run_l2_revision_query_setter(...)
l2_revision_query_frame_data_id(...)
```

`run_l2_revision_query_setter(...)`는 다음만 수행한다.

1. `L2:revision_query_plan:{attempt}` record를 읽는다.
2. `selected_candidate_id`가 가리키는 후보의 query/tool을 찾는다.
3. `L2:revision_query_frame:{attempt}` record를 만든다.

## 저장되는 record

예시:

```text
data_id: L2:revision_query_frame:0001
data_type: node_output:L2_revision_query_frame
query_source: revision_llm_query_plan
target_tool_name: search_docs
```

## 메타정보 경계

이 단계는 LLM이 만든 후보 중 선택된 후보를 복사하는 단계다.

코드는 다음을 하지 않는다.

- 후보 query가 의미적으로 더 좋은지 판정하지 않는다.
- L3 feedback 문장을 해석하지 않는다.
- 문서 후보 내용을 사실로 단정하지 않는다.
- 도구 실행 성공을 미리 선언하지 않는다.

코드는 다음만 한다.

- 선택 후보 ID 확인
- query/tool 복사
- 출처 trace/data 연결
- 스키마 검증

## 아직 하지 않은 것

아직 다음 흐름은 연결하지 않았다.

```text
L2:revision_query_frame:{attempt}
-> tool choice
-> search_docs/read_artifact 실행
-> distillation
-> budget 갱신
-> L3 재판정
```

다음 단계는 revision query frame을 실제 tool runner에 연결하는 것이다.

## 검증

```text
python -m compileall songryeon_core main.py dry_run.py
python main.py smoke-test
```

검증 결과:

```text
SMOKE_TEST_OK
l2_revision_query_frame_source = revision_llm_query_plan
l2_revision_query_frame_tool = search_docs
```

