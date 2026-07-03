# order_166_night_time_bundle_summary_node_2026_07_02_001

## Summary

ORDER 166을 구현했다.

이번 작업은 심야정부가 `TimeBundle` graph node 하나를 대상으로 LLM summary node를 만들 수 있게 하는 첫 MVP다.

핵심 원칙:

```text
원본 TimeBundle은 code-generated absolute 좌표로 그대로 둔다.
LLM 요약은 별도 SummaryGraphNode로 만든다.
SummaryGraphNode -> TimeBundle 방향의 SUMMARY_OF edge를 붙인다.
```

## Changed Files

- `Administrative_Reform_1/04_Orders/ORDER_166_NIGHT_TIME_BUNDLE_SUMMARY_NODE_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `songryeon_core/core/schema_parts/graph_memory.py`
- `songryeon_core/core/schema_parts/__init__.py`
- `songryeon_core/core/schemas.py`
- `songryeon_core/core/graph_vessel_neo4j.py`
- `songryeon_core/nodes/night_time_bundle_summary_worker.py`
- `songryeon_core/prompts/night_time_bundle_summary_worker_v0.md`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_166_night_time_bundle_summary_node.py`

## Implementation Notes

Added `NightTimeBundleSummaryFrame`.

The frame records:

- `summary_graph_node_id`
- `target_graph_node_id`
- `summary_text`
- `summary_status`
- `failure_type`
- `summary_depth`
- `source_leaf_count`
- `source_summary_count`
- `source_graph_node_ids`
- `validity_status`
- `review_status`
- `llm_call_data_id`
- `generated_by`
- `info_class`
- `semantic_judgement_status`

The summary worker is `songryeon_core/nodes/night_time_bundle_summary_worker.py`.

On success it records:

- `graph_memory:node:summary`
- `graph_memory:edge:SUMMARY_OF`

On adapter/schema/parse failure it records only:

- `node_output:night_time_bundle_summary_frame`

It does not create a fake graph summary node on failure.

## Metainfo Classification

Code decides `info_class` only from source cardinality.

```text
source_leaf_count == 1
and source_summary_count == 0
and len(source_graph_node_ids) == 1
-> relative

otherwise
-> mixed
```

Code does not write `summary_text`.

LLM writes `summary_text`.

If the LLM supplies an incompatible `info_class`, the payload is rejected and a failed frame is recorded.

## Vessel / Export Behavior

Existing export behavior already includes `graph_memory:node:*` and `graph_memory:edge:*`.

Therefore successful summary records are included as graph node and graph edge export items.

The Vessel write plan treats:

- summary node as `upsert_graph_node`
- `SUMMARY_OF` edge as `upsert_graph_edge`

Neo4j display vocabulary now gives summary nodes the `SummaryGraphNode` label and a readable display name.

## Deliberately Not Opened

- R loop automatic use of the summary node
- live R1/R2/R3 LLM traversal
- semantic axis
- node_4 approval loop for graph summary
- mutation of original `TimeBundle`
- weakening `GraphMemoryNodeFrame` absolute lock
- code-generated semantic summary text

## Verification

```powershell
python -m compileall songryeon_core main.py
```

Passed.

```powershell
python -m pytest tests/test_order_166_night_time_bundle_summary_node.py -q
```

Passed: `4 passed`.

```powershell
python main.py fast-test --profile graph
```

Passed: `FAST_TEST_OK`, graph pytest `78 passed`.

```powershell
python -m pytest -q
```

Passed after increasing timeout: `209 passed in 686.63s`.

First full pytest attempt timed out at about 424 seconds before completion, so it was rerun with a longer limit.

```powershell
python main.py smoke-test
```

Passed: `SMOKE_TEST_OK`.

```powershell
git diff --check
```

Passed.

## Remaining Risk

Current `RawCapsule` graph nodes mainly expose trace/capsule coordinates, not full previous conversation text.

Therefore this MVP proves the summary node/edge/schema/export path, but rich conversation-content summarization still needs a later order that supplies original text or approved source snapshots to the night worker.
