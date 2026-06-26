# L2 Revision Query Planner 2026-06-24 001

## 목적

`L2RevisionInputFrame`을 받은 L2가 재검색 계획을 만들 수 있게 했다.

이번 구현은 L2가 새 검색어 후보를 계획하는 단계까지만 다룬다.

아직 실제 도구 실행과 L3 재판정은 연결하지 않았다.

```text
L2RevisionInputFrame
-> L2 revision query planner
-> L2:revision_query_plan:{attempt}
```

## 구현 파일

- `songryeon_core/core/schemas.py`
- `songryeon_core/nodes/l2_query_setter.py`
- `songryeon_core/prompts/l2_revision_query_setter_v0.md`
- `songryeon_core/llm/fake.py`
- `songryeon_core/runtime/smoke_test.py`
- `Administrative_Reform_1/04_Orders/ORDER_089_L_LOOP_CONTINUATION_V0.md`

## 추가된 planner mode

```text
revision_llm
revision_fallback
```

이번 smoke에서는 `revision_llm`만 사용했다.

## 새 함수

```text
run_l2_revision_query_planner(...)
l2_revision_query_plan_data_id(...)
```

`run_l2_revision_query_planner(...)`는 다음을 수행한다.

1. `L2RevisionInputFrame` record를 읽는다.
2. revision 전용 프롬프트를 사용해 LLM에게 새 query 후보를 요청한다.
3. 결과를 `L2QueryPlanFrame`으로 검증한다.
4. attempt별 record로 저장한다.

저장되는 data id 예시:

```text
L2:revision_query_plan:0001
```

data type:

```text
node_output:L2_revision_query_plan_frame
```

## 새 프롬프트

```text
songryeon_core/prompts/l2_revision_query_setter_v0.md
```

핵심 원칙:

- 이전 검색어를 그대로 반복하지 않는다.
- L3 feedback은 참고하되 절대정보로 다루지 않는다.
- `search_docs`는 의미 검색용으로 사용한다.
- `read_artifact`는 명시 문서명/경로가 있을 때만 사용한다.
- `read_doc`, `list_docs`는 L2가 직접 고르지 않는다.
- 재시도가 이미 성공했다고 말하지 않는다.

## fake adapter

테스트용으로 다음 adapter를 추가했다.

```text
RevisionQueryPlannerFakeLLMAdapter
```

이 adapter는 `revision_input`을 읽고, 이전 검색어와 다른 revision query 후보를 만든다.

## 아직 하지 않은 것

아직 live L루프 내부에서 다음 흐름은 연결하지 않았다.

```text
revision query plan
-> selected query
-> tool choice
-> search_docs/read_artifact 실행
-> L3 재판정
```

다음 단계는 revision plan에서 선택된 후보를 실제 attempt별 query frame으로 바꾸고, 도구 실행을 이어붙이는 것이다.

## 검증

```text
python -m compileall songryeon_core main.py dry_run.py
python main.py smoke-test
```

검증 결과:

```text
SMOKE_TEST_OK
l2_revision_query_plan_mode = revision_llm
l2_revision_query_plan_selected = find_requested_internal_document revised evidence after partial
```

