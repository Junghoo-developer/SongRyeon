# ORDER 188 Execution Record: R Vessel Raw Original Read Cap

## Date

2026-07-03

## Scope

Implemented a hard cap for raw original material inspection in R Vessel traversal.

## Changed Files

- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/runtime/r_loop_vessel_one_step.py`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_188_r_vessel_raw_original_cap.py`
- `Administrative_Reform_1/04_Orders/ORDER_188_R_VESSEL_RAW_ORIGINAL_READ_CAP_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `Administrative_Reform_1/05_Execution_Records/README.md`

## Implementation Notes

- Added `R_TRAVERSE_MAX_RAW_ORIGINAL_MATERIAL_READS = 5`.
- Added result frame fields:
  - `raw_original_material_seen_count`
  - `max_raw_original_material_count`
  - `raw_original_read_cap_reached`
- Raw original material is counted only for `RawSource` and `RawCapsule`.
- Summary nodes are not counted as raw original reads.
- If R3 wants to continue after 5 raw original reads, code returns:

```text
continuation_status=stop_budget_exhausted
continuation_reason_code=CODE_STATUS:r_loop_raw_original_read_cap_reached
```

## Boundary

This is an absolute budget guard. Code counts raw-original inspections but does not judge their semantic value.

## Verification

Passed:

```text
python -m compileall songryeon_core main.py
python -m pytest -q tests/test_order_188_r_vessel_raw_original_cap.py
python -m pytest -q tests/test_order_184_r_vessel_multi_step_traversal.py tests/test_order_185_r_terminal_material_guard.py tests/test_order_186_r_vessel_exact_child_expansion.py tests/test_order_187_r_vessel_summary_layer_before_raw.py tests/test_order_188_r_vessel_raw_original_cap.py
python main.py fast-test --profile graph
python main.py smoke-test
git diff --check
```

Observed:

```text
ORDER 188 tests: 2 passed
ORDER 184-188 focused tests: 9 passed
graph fast-test: FAST_TEST_OK, 140 passed
smoke-test: SMOKE_TEST_OK
diff check: clean
```

During verification, graph fast-test initially caught a misplaced `max_raw_original_material_reads`
check in the one-step R runner. The one-step runner does not own this cap, so the stray check was
removed and graph fast-test was rerun successfully.

## Remaining Risk

This cap is enforced inside current R Vessel traversal. If future R implementations add a separate raw-fetch tool outside this traversal path, the same cap must be mirrored there.
