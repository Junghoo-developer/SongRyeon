# ORDER 196 R Vessel Activity Ledger Raw Capsule Link Implementation

Date: 2026-07-03

## Summary

ORDER 196 is implemented.

The Vessel-backed R traversal activity ledger can now be linked from the current turn's raw capsule graph node through the existing turn activity graph link mechanism.

Elementary explanation:

```text
Before:
The turn capsule existed.
The R Vessel activity ledger existed.
But there was no explicit graph card saying, "this turn's capsule has this R activity ledger."

After:
The raw capsule graph node has a HAS_ACTIVITY_LEDGER edge to the R Vessel activity ledger graph node.
```

## Code Changes

- `songryeon_core/core/schema_parts/graph_memory.py`
  - Added `r_vessel_activity_ledger` as a supported turn activity graph link kind.
  - Added `r_vessel_activity_ledger_data_ids` to `TurnActivityGraphLinkFrame`.
  - Kept validation strict: all listed ledger IDs must also be present in `source_data_ids`.

- `songryeon_core/core/turn_activity_graph_links.py`
  - Added `R_VESSEL_ACTIVITY_LEDGER_DATA_TYPE`.
  - Extended `record_turn_activity_graph_links(...)` with `r_vessel_activity_ledger_data_ids`.
  - Creates an activity ledger graph node with `data_kind=r_vessel_activity_ledger`.
  - Creates a `HAS_ACTIVITY_LEDGER` edge from `graph:raw_capsule:{turn_id}` to the R Vessel activity ledger graph node.

- `songryeon_core/runtime/r_loop_vessel_one_step.py`
  - After recording `RLoopVesselActivityLedgerFrame`, the local Vessel R traversal runtime now records a turn activity graph link.
  - Runtime output now exposes the raw-capsule-to-R-ledger link counts.

- `tests/test_order_196_r_vessel_activity_raw_capsule_link.py`
  - Added focused tests for direct graph link creation, missing-ledger no-op behavior, and runtime integration.

## Boundaries Preserved

- No Neo4j write was added by this order.
- No R answer route was added.
- No node_0 checkpoint loop was added.
- No relevance or importance judgement was inferred by code.
- No raw capsule rewrite or deletion was added.
- No L/R traversal policy was changed.

## Verification

Passed:

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_196_r_vessel_activity_raw_capsule_link.py -q
python -m pytest tests/test_order_152_raw_capsule_activity_graph_link.py tests/test_order_194_r_vessel_start_handoff.py tests/test_order_195_r_vessel_activity_ledger.py tests/test_order_196_r_vessel_activity_raw_capsule_link.py -q
python main.py smoke-test
python -m pytest -q
python -m pytest tests/test_order_151_l_loop_activity_ledger.py::test_l_loop_activity_ledger_is_recorded_from_dry_turn tests/test_smoke_baseline.py::test_smoke_test_baseline_status_ok -q
git diff --check
```

Observed focused result:

```text
3 passed
13 passed
SMOKE_TEST_OK
full pytest first pass: 290 passed, 2 failed with PermissionError on .songryeon_core_cache/document_memory_indexes/snapshot_b736778bb1778507.json
failed tests rerun: 2 passed
```

The full pytest failures were the recurring document memory index cache write lock on OneDrive.
The exact failed tests passed when rerun without code changes.

## Remaining Work

ORDER 196 only links the R Vessel activity ledger to the raw capsule.

It does not yet make node_0 inject mid-R-loop memory packets, does not persist R loop progress into a live TurnStateCapsule during traversal, and does not connect the R ledger into Neo4j unless a later export/write path includes these graph memory records.
