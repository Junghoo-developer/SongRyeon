# Tool Catalog Choice 2026-06-22 001

## 목적

ORDER 046에 따라 LLM과 노드가 사용할 수 있는 도구 목록과 도구 선택 결과를 구조화했다.

## 변경 내용

- `ToolCatalogFrame`, `ToolCatalogItem`, `ToolChoiceFrame` 스키마를 추가했다.
- `ToolSpec`에 `input_fields`를 추가했다.
- `ToolRegistry`가 catalog item 목록을 만들 수 있게 했다.
- L루프가 `tool_catalog:<turn_id>`를 DataStore에 저장한다.
- L2가 `tool_choice:L2:search_docs`를 저장한 뒤 `search_docs`를 실행한다.
- `ToolChoiceFrame.tool_name`은 `ToolRegistry.get()`으로 검증된다.
- smoke test가 catalog와 choice를 확인한다.

## 확인 결과

```text
python dry_run.py
DRY_RUN_OK
trace_count=17
data_record_count=17
movement_count=11

python main.py smoke-test
SMOKE_TEST_OK
tool_catalog_count=3
tool_choice='search_docs'
```

Fake L2 planner 실행 예시:

```text
trace_count=19
data_record_count=19
catalog_tools=['list_docs', 'read_doc', 'search_docs']
choice='search_docs'
plan_sources=[
  'L1:goal_frame',
  'tool_catalog:turn_dry_001',
  'llm_call:L2:trace_000007'
]
query_source='llm_query_plan'
```

## 해석

이번 단계부터 LLM에게 도구 설명을 매번 사람이 풀어줄 필요가 줄어든다.

코드가 registry에서 도구 catalog를 만들고, L2는 그 catalog를 근거로 tool choice를 남긴다. 도구 실행은 여전히 코드가 맡는다. 따라서 LLM은 도구를 직접 실행하지 않고, 구조화된 선택을 제안하거나 남기는 역할에 머문다.
