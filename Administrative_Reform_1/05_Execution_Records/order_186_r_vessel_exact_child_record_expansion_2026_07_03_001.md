# ORDER 186 Execution Record: R Vessel Exact Child Record Expansion

## Date

2026-07-03

## Scope

Implemented a structural R Vessel read packet expansion so that exact child graph records referenced by visible parent candidates are included in the packet even when they appear outside the base entry row limit.

## Changed Files

- `songryeon_core/core/r_loop_vessel_read_packet.py`
- `songryeon_core/runtime/r_loop_vessel_read_packet.py`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_186_r_vessel_exact_child_expansion.py`
- `Administrative_Reform_1/04_Orders/ORDER_186_R_VESSEL_EXACT_CHILD_RECORD_EXPANSION_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `Administrative_Reform_1/05_Execution_Records/README.md`

## Implementation Notes

- Added `R_LOOP_VESSEL_EXACT_CHILD_EXPANSION_V0`.
- `RLoopVesselReadPacketFrame` now records:
  - `exact_child_expansion_policy_id`
  - `base_entry_candidate_count`
  - `exact_child_expanded_entry_count`
  - `exact_child_expanded_node_ids`
  - `exact_child_expansion_truncated`
- The packet builder keeps the base `limit`, then follows exact child IDs from visible entry candidates:
  - payload `source_graph_node_ids`
  - record `parent_graph_node_ids`
- Expansion is bounded by:
  - max depth: 2
  - max additional records: the same numeric `limit`

## Boundary

This change does not rank, summarize, or semantically select graph nodes. Code only follows explicit graph IDs and records the result as absolute information.

R2 still chooses from official refs, and R3 still evaluates sufficiency/depth.

## Verification

Passed:

```text
python -m compileall songryeon_core main.py
python -m pytest -q tests/test_order_186_r_vessel_exact_child_expansion.py
python -m pytest -q tests/test_order_175_vessel_backed_r_read_packet.py tests/test_order_183_r_vessel_hierarchical_child_surface.py tests/test_order_184_r_vessel_multi_step_traversal.py tests/test_order_185_r_terminal_material_guard.py tests/test_order_186_r_vessel_exact_child_expansion.py
python main.py fast-test --profile graph --skip-compileall
python main.py fast-test --profile graph
python main.py smoke-test
python main.py vessel-r-read-packet --database neo4j --format text
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 source summary와 token layer summary가 어떻게 이어지는지 계층적으로 탐색해줘" --database neo4j --llm-mode fake --format text
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 source summary와 token layer summary가 어떻게 이어지는지 계층적으로 탐색해줘" --database neo4j --llm-mode qwen --timeout 180 --format text
```

Observed:

```text
tests/test_order_186_r_vessel_exact_child_expansion.py: 2 passed
ORDER 175/183/184/185/186 bundle: 14 passed
fast-test graph: 136 passed
fast-test graph with compileall: 136 passed
smoke-test: SMOKE_TEST_OK
vessel-r-read-packet: entry_candidate_count=100, base_entry_candidate_count=50, exact_child_expanded_entry_count=50, exact_child_expansion_truncated=True
vessel-r-traverse fake: TimeAxis -> SourceIngestBundle -> SourceKindBundle -> RawSource, terminal_material_seen_count=1
vessel-r-traverse qwen: TimeAxis -> SourceIngestBundle -> SourceKindBundle -> RawSource, terminal_material_seen_count=1
```

## Remaining Risk

This unblocks exact child visibility, but it does not yet make R traversal semantically sharp. If a bundle has many children, R2 still needs better layer-level and budget-level selection policies in later orders.
