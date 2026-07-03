# ORDER 179: R2 Vessel Selection ID Disambiguation v0

## Status

Proposed after the first live ORDER_178 Qwen test on 2026-07-02.

## Trigger

Live command:

```powershell
python main.py vessel-r-one-step "송련 Core의 그래프 기억 구조에서 source summary와 token layer summary가 어떻게 이어지는지 한 단계만 골라봐" --database neo4j --llm-mode qwen --timeout 120 --format text
```

Observed result:

- `read_packet_status=passed`
- `entry_candidate_count=3`
- `summary_candidate_count=50`
- `failure_stage=R2`
- `failure_type=schema_failed`
- `failure_reason=R2 selected_graph_node_id must be in available_graph_node_ids`

## Problem

ORDER_178 added candidate layer surfaces, but R2 can still confuse selection IDs with explanatory/source IDs inside candidate records.

Most likely confusion:

- should select: `graph_node_id`
- may have selected instead: `target_graph_node_id`, `source_graph_node_ids`, or other source/target IDs

This is not a reason to weaken validation. It is a payload clarity and diagnostics issue.

## Goal

Make R2's selectable ID field unambiguous and make failed R2 payloads visible enough to debug.

## Scope

- R2 candidate records expose `graph_node_id` as the only direct selectable graph node field.
- R2 candidate records do not expose `target_graph_node_id` or `source_graph_node_ids`.
- R2 prompt explicitly says:
  - choose `selected_surface_id` from `available_surface_ids`
  - choose `selected_graph_node_id` by copying a candidate record's `graph_node_id`
  - do not use target/source/data IDs as selected graph node IDs
- Failed R2 schema validation records/prints a compact payload summary:
  - selected surface ID
  - selected graph node ID
  - whether the surface ID was allowed
  - whether the graph node ID was globally allowed
  - whether the graph node ID belonged to the selected surface

## Non-Goals

- Do not allow invalid selected graph node IDs.
- Do not let code choose a semantic fallback candidate.
- Do not add two-stage R2a/R2b yet.
- Do not open multi-step R traversal.
- Do not change Neo4j schema or write behavior.

## Completion Criteria

- `python -m compileall songryeon_core main.py`
- `python -m pytest tests/test_order_176_vessel_r_one_step_traversal.py tests/test_order_177_r1_candidate_text_blindness.py tests/test_order_178_r_vessel_candidate_layer_surface.py tests/test_order_179_r2_vessel_selection_id_disambiguation.py -q`
- `python main.py fast-test --profile graph`
- `git diff --check`

