# ORDER 166: Night TimeBundle Summary Node v0

## 1. Goal

심야정부가 `TimeBundle` graph node 하나를 대상으로 LLM 요약 graph node를 생성할 수 있는 최소 MVP를 만든다.

이번 발주의 핵심은 원본 `TimeBundle` payload를 수정하지 않고, 별도 `SummaryGraphNode`를 만들어 `SUMMARY_OF` edge로 연결하는 것이다.

```text
TimeBundle
  <- SUMMARY_OF
SummaryGraphNode
```

## 2. Background

철학 문서 기준:

- raw/time bundle graph node는 code-generated absolute coordinate다.
- LLM 요약은 원본 속성이 아니라 별도 summary node다.
- raw leaf 1개를 직접 보고 만든 요약은 `relative`다.
- raw leaf 여러 개 또는 bundle을 보고 만든 요약은 `mixed`다.
- summary node는 source bundle, generated_by, info_class, semantic_judgement_status, summary_depth를 드러내야 한다.

현재 Core에는 이미 다음 기반이 있다.

- `CoreEgo -> TimeAxis -> TimeBundle -> RawCapsule`
- `GraphMemoryNodeFrame` absolute lock
- `SUMMARY_OF` edge kind
- summary invalidation ledger foundation
- graph export packet / Vessel write plan / Neo4j writer

## 3. Scope

### 3.1 New summary frame

Add a dedicated summary frame for LLM-generated graph summaries.

Required fields:

- `node_id`
- `node_kind=summary`
- `target_graph_node_id`
- `target_node_kind`
- `summary_text`
- `summary_depth`
- `source_depth_min`
- `source_depth_max`
- `source_leaf_count`
- `source_summary_count`
- `source_bundle_kind`
- `source_graph_node_ids`
- `source_trace_ids`
- `source_data_ids`
- `validity_status`
- `review_status`
- `llm_call_data_id`
- `llm_trace_event_id`
- `prompt_ref`
- `generated_by`
- `info_class`
- `semantic_judgement_status`

### 3.2 Classification rule

Code may classify only by source cardinality and target structure, not by semantic content.

```text
source_leaf_count == 1 and len(source_graph_node_ids) == 1
-> info_class=relative

otherwise
-> info_class=mixed
```

If an LLM payload supplies an incompatible `info_class`, validation fails. Code does not silently correct the semantic text.

### 3.3 LLM boundary

LLM writes:

- `summary_text`

Code writes/checks:

- target node coordinates
- source ids
- summary depth/count fields
- info_class classification by source cardinality
- validity/review status
- schema and allowed ID validation

If adapter is missing or fails, no fake summary is created. A failed summary frame may be recorded with empty `summary_text`, `semantic_judgement_status=failed`, and failure diagnostics.

### 3.4 Storage/export

The summary is recorded as `graph_memory:node:summary`.

The `SUMMARY_OF` edge is recorded as `graph_memory:edge:SUMMARY_OF`.

Graph export and Vessel write plan should include the summary node and summary edge through existing graph node/edge export behavior.

## 4. Non-goals

- Do not mutate `TimeBundle` payload.
- Do not weaken `GraphMemoryNodeFrame` absolute lock.
- Do not open semantic axis.
- Do not auto-feed summary into R loop answers.
- Do not open R1/R2/R3 live LLM traversal.
- Do not add node_4 approval loop yet.
- Do not delete or overwrite old summary nodes.
- Do not make code write semantic summary text.

## 5. Test Plan

Required:

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_166_night_time_bundle_summary_node.py
python main.py fast-test --profile graph
git diff --check
```

Additional test expectations:

- multi-leaf `TimeBundle` summary is `mixed`.
- single-leaf `TimeBundle` summary may be `relative`.
- incompatible LLM `info_class` fails and records failed status without fake summary text.
- original `TimeBundle` remains `absolute/not_run`.
- summary node has `summary_depth=1` for raw leaf bundle sources.
- `SUMMARY_OF` edge points from summary node to target time bundle.
- export packet includes summary node and summary edge.
- Vessel write plan treats summary node as graph node operation, not support record.

## 6. Completion Report Must Include

- where summary frame/schema was added
- how `relative` vs `mixed` is decided
- how failed LLM summary is handled
- how original TimeBundle stays clean
- export/write-plan behavior
- test results
