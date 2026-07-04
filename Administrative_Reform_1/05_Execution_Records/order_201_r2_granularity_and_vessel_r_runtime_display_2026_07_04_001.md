# ORDER 201 R2 Granularity And Vessel R Runtime Display - 2026-07-04 001

## Summary

Implemented the narrow fix after the first live gated Vessel R test.

The live route reached R, but R2 failed because `expected_information_granularity` did not match the strict enum. The runtime also displayed the Vessel-backed path as the older skeleton R path.

## Changed Files

- `Administrative_Reform_1/04_Orders/ORDER_201_R2_GRANULARITY_AND_VESSEL_R_RUNTIME_DISPLAY_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/prompts/r2_vessel_node_selector_v0.md`
- `songryeon_core/nodes/node_2_handoff.py`
- `songryeon_core/runtime/dry_run.py`
- `songryeon_core/runtime/terminal_view.py`
- `songryeon_core/tools/document_memory_index.py`
- `tests/test_order_200_vessel_r_live_gated_integration.py`
- `tests/test_order_201_r2_granularity_and_vessel_r_display.py`

## Implementation Notes

- Added `R_INFORMATION_GRANULARITY_ENUM_VALUES`.
- Added `allowed_information_granularity_values` to the R2 LLM payload.
- Added `expected_information_granularity_contract` to the R2 LLM payload.
- Updated `r2_vessel_node_selector_v0.md` to require exact copying from the supplied enum list.
- Kept R2 validator strict; invalid enum output still fails.
- Did not add hidden normalization or fallback repair.
- Updated route path rendering to distinguish:
  - old frame-only skeleton R
  - Vessel-backed R live path
- Updated terminal activity graph display to show `R_vessel_ledgers` separately.
- Added `route2_handoff_path` to `run_dry_turn()` result summary.
- Hardened document memory index cache saving:
  - same payload cache writes are skipped
  - changed payload writes go through a temporary file and `os.replace`
  - transient `PermissionError` against an existing cache file does not abort the current run

This cache hardening was added because `python main.py smoke-test` repeatedly hit a OneDrive-local cache write `PermissionError` on `.songryeon_core_cache/document_memory_indexes/snapshot_c64f59af0fdf8436.json`.

## Verification

Commands:

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_201_r2_granularity_and_vessel_r_display.py -q
python -m pytest tests/test_order_200_vessel_r_live_gated_integration.py -q
python -m pytest tests/smoke/test_document_memory.py tests/test_order_201_r2_granularity_and_vessel_r_display.py tests/test_order_200_vessel_r_live_gated_integration.py -q
python main.py smoke-test
git diff --check
```

Focused results before smoke:

- ORDER 201 focused pytest: `2 passed`
- ORDER 200 focused pytest: `3 passed`
- compileall: passed
- document memory + ORDER 201 + ORDER 200 pytest: `6 passed`
- smoke-test: `SMOKE_TEST_OK`
- `git diff --check`: passed

Post-patch live observation:

- Command shape: `python main.py qwen-turn "... Vessel R 그래프 기억 ..." --enable-vessel-r-route --database neo4j --timeout 180 --pretty`
- Node 1 selected `route=R`.
- Runtime route path displayed the Vessel-backed path:
  - `1:route=R_vessel_experimental`
  - `0:vessel_r_read_packet`
  - `0:vessel_r_start_handoff`
  - `R:Vessel_R1_R2_R3_traverse`
  - `0:vessel_r_return_packet`
- Turn activity graph links displayed `R_vessel_ledgers=1`.
- R traversal completed with `task=sufficient`.
- Node 3 received Vessel R material: `items=6 / summaries=3 / raw_originals=0`.
- Node 4 blocked the final answer with `CODE_STATUS:vessel_r_material_claim_mismatch` because the generated report leaked Vessel graph node IDs.

Conclusion: ORDER 201's target issue is fixed. The next visible blocker is not R2 granularity or runtime path honesty; it is node 3 / node 4 handling of user-facing Vessel graph IDs.

## Boundaries Preserved

- Route `R` is still not enabled by default.
- R2 schema validation was not weakened.
- No code semantic fallback or enum repair was added.
- No Neo4j write path was changed.
- No scheduler/background R route was added.
