# ORDER 187 Execution Record: R Vessel Summary Layer Before Raw

## Date

2026-07-03

## Scope

Implemented a structural R traversal policy so that `SourceKindBundle` exposes active summary-layer children before direct raw source children.

## Changed Files

- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_187_r_vessel_summary_layer_before_raw.py`
- `Administrative_Reform_1/04_Orders/ORDER_187_R_VESSEL_SUMMARY_LAYER_BEFORE_RAW_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `Administrative_Reform_1/05_Execution_Records/README.md`

## Implementation Notes

- Added source-kind summary-layer child selection inside R Vessel hierarchy child generation.
- For a selected `SourceKindBundle`, code gathers raw child IDs from:
  - selected record `source_graph_node_ids`
  - entry records whose `parent_graph_node_ids` include the selected source-kind node
- Code then finds active summary candidate records that explicitly cover those raw IDs through:
  - `source_data_ids`
  - `source_graph_node_ids`
  - `target_graph_node_id`
- Priority is structural:
  - `token_budget_bundle_summary`
  - then `source_leaf_summary`
  - then fallback to raw source children
- `hierarchy_child_node_ids` now acts as the official code-built child list. When present, it prevents raw `source_graph_node_ids` from being appended back into the R3 child list.

## Boundary

No semantic relevance judgement was added. Code does not inspect summary text or choose the best summary by meaning.

R2 still chooses from official refs. R3 still judges sufficiency.

## Verification

Passed:

```text
python -m compileall songryeon_core main.py
python -m pytest -q tests/test_order_187_r_vessel_summary_layer_before_raw.py
python -m pytest -q tests/test_order_183_r_vessel_hierarchical_child_surface.py tests/test_order_184_r_vessel_multi_step_traversal.py tests/test_order_185_r_terminal_material_guard.py tests/test_order_186_r_vessel_exact_child_expansion.py
python main.py fast-test --profile graph
python main.py smoke-test
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 source summary와 token layer summary가 어떻게 이어지는지 계층적으로 탐색해줘" --database neo4j --llm-mode fake --format text
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 source summary와 token layer summary가 어떻게 이어지는지 계층적으로 탐색해줘" --database neo4j --llm-mode qwen --timeout 180 --format text
```

Observed:

```text
ORDER 187 tests: 2 passed
ORDER 183/184/185/186 bundle: 8 passed
fast-test graph: 138 passed
smoke-test: SMOKE_TEST_OK
vessel-r-traverse fake: TimeAxis -> SourceIngestBundle -> SourceKindBundle -> token_budget_bundle_summary, terminal_material_seen_count=1, stop_sufficient
vessel-r-traverse qwen: TimeAxis -> SourceIngestBundle -> SourceKindBundle -> token_budget_bundle_summary, terminal_material_seen_count=1, stop_budget_exhausted because R3 wanted deeper after the token summary
```

## Remaining Risk

This only changes the first layer exposed under `SourceKindBundle`. It does not yet build a full semantic-axis navigator, nor does it make R1 truly set traversal budgets.
