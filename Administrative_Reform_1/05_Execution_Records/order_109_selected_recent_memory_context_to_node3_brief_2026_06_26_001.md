# ORDER_109 selected recent memory context to node3 brief execution record

## 대상

- `Administrative_Reform_1/04_Orders/ORDER_109_SELECTED_RECENT_MEMORY_CONTEXT_TO_NODE3_BRIEF_V0.md`

## 구현 상태

구현됨.

## 핵심 변경

`songryeon_core/nodes/node_2_handoff.py`

- memory selector가 고른 후보 turn id를 `ZeroState.recent_raw_conversation`의 `turn_id`와 정확히 맞춰 찾는다.
- 선택된 raw user/assistant text를 요약 없이 복사해 selected recent memory context로 저장한다.
- 대응 원문이 없으면 missing count로 남기고 억지 fallback을 하지 않는다.

`songryeon_core/core/schemas.py`

- node_3 brief가 선택된 최근 기억 context를 구조적으로 받을 수 있게 schema가 확장되어 있다.

`songryeon_core/prompts/node_3_reporter_v0.md`

- node_3는 선택된 최근 기억 context가 있을 때 그 raw text 범위 안에서만 이전 대화를 언급하도록 경계가 들어가 있다.

## Smoke 기준선

`python main.py smoke-test`에서 다음 확인값을 본다.

```text
selected_recent_memory_context_copied=1
selected_recent_memory_context_none_empty=true
selected_recent_memory_context_missing=1
selected_recent_memory_context_truncated=true
selected_recent_memory_context_node3_answer=파란노트
memory_selection_node3_selected_count=1
memory_selection_no_raw_answer_leak=true
```

## 범위 밖

- 최근 기억 관련성 code heuristic fallback
- 선택되지 않은 과거 원문 자동 삽입
- 기억 요약
- 장기기억 DB
- node_5 compression 실행
