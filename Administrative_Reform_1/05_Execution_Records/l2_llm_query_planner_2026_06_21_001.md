# L2 LLM Query Planner 2026-06-21 001

## 목적

ORDER 045에 따라 L2가 사용자 입력 fallback만 쓰지 않고, LLM으로 내부 문서 검색 query 후보를 계획할 수 있게 했다.

## 변경 내용

- `L2QueryPlanFrame`과 `L2QueryPlanCandidate` 스키마를 추가했다.
- `L2QueryFrame.query_source`에 `llm_query_plan`을 허용했다.
- `QueryPlannerFakeLLMAdapter`를 추가했다.
- L2에 `run_l2_query_planner()`를 추가했다.
- L루프가 선택적으로 L2 query planner adapter를 받아 query plan을 실행한다.
- LLM planner 실패 시 기존 `user_input_fallback`으로 검색한다.
- smoke test가 L2 planner 성공과 깨진 JSON fallback을 확인한다.

## 확인 결과

```text
python main.py smoke-test
SMOKE_TEST_OK
l2_query_plan_candidates=2
l2_broken_planner_fallback=true
```

Fake planner 실행 예시:

```text
has_plan=true
query_source='llm_query_plan'
query_text='내부 문서 자동 검색'
data_count=17
trace_count=17
```

근거 연결 확인:

```text
L2:query_plan_frame.source_data_ids=[
  'L1:goal_frame',
  'llm_call:L2:trace_000006'
]
```

## 해석

이번 단계부터 L2는 검색어 후보를 여러 개 만들 수 있다.  
다만 LLM이 도구를 직접 실행하지는 않는다. LLM은 `L2QueryPlanFrame`을 만들고, 코드는 선택된 후보를 검증해 `L2QueryFrame`으로 이어 보낸다.

LLM planner가 JSON 파싱에 실패하면 `LLMCallFrame`에 실패가 기록되고, 검색은 기존 사용자 입력 fallback으로 계속 진행된다.
