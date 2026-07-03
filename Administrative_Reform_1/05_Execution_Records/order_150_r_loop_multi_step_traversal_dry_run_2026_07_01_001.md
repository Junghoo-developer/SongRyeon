# ORDER 150 R Loop Multi-Step Traversal Dry-Run Implementation

Date: 2026-07-01

## Summary

Implemented ORDER_150 as a dry-run-only multi-step R traversal.

The R skeleton now consumes `RGraphTraversalCandidateSurfaceFrame` and can move from:

```text
graph:axis:time
  -> graph:time_bundle:{turn_id}
      -> graph:raw_capsule:{turn_id}
```

within the existing dry-run fixture.

## Code Changes

- `songryeon_core/loops/r_loop_dry_run.py`
  - `run_r_loop_dry_run_skeleton()` now loops across candidate surfaces while continuation says `R2` and budget remains.
  - Added step-indexed frame ids:
    - `R:...:budget_frame:0001`
    - `R2:...:graph_node_selection_frame:0001`
    - `R3:...:graph_inspection_frame:0001`
    - `R:...:graph_traversal_candidate_surface_frame:0001`
    - `R:...:continuation_frame:0001`
  - R2 step 2+ selects only from the previous candidate surface coordinate list.
  - Return summary and access ledger now accumulate all selected/inspected/candidate graph node ids.
  - Added optional in-memory graph payload views for experimental R route so it can inspect graph nodes without permanently recording provisional graph nodes into DataStore.

- `songryeon_core/runtime/dry_run.py`
  - Added `r_route_dry_run_traversal_step_count`.
  - Experimental R route now passes build-only graph payloads into the skeleton instead of persisting provisional graph nodes.

- `tests/test_order_150_r_loop_multi_step_traversal_dry_run.py`
  - Added tests for candidate-surface consumption, depth counting, access ledger accumulation, and forced budget exhaustion.

## Budget Semantics

- Entry node inspection uses traversal depth `0`.
- Moving through one graph edge uses traversal depth `1`.
- With `max_traversal_depth=2`, dry-run can reach `raw_capsule` from `time_axis`.
- Node read count follows inspected graph node count.

## Guardrails Preserved

- No live R route expansion.
- No R LLM traversal.
- No external DB / Neo4j connection.
- No semantic ranking.
- No graph summarization.
- No node_3 answer behavior expansion.

## Verification

Passed:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

Pytest result:

```text
137 passed in 535.04s
```

Smoke result:

```text
SMOKE_TEST_OK
```

## Observed Runtime Baseline

Default R dry-run now reports:

```text
r_route_dry_run_status=sufficient
r_route_dry_run_continuation=stop_sufficient
```

This replaces the previous single-step baseline where dry-run stopped at `continue_deeper`.

## Remaining Risk

R traversal is still deterministic dry-run wiring. It proves that graph traversal frames, candidate surfaces, budgets, summaries, and ledgers can chain across multiple steps. It does not yet prove semantic graph search quality.
