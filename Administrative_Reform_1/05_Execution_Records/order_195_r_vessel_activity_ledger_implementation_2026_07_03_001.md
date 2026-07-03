# ORDER 195 R Vessel Activity Ledger Implementation 2026-07-03 001

## Summary

Implemented the Vessel R activity ledger.

Before this patch, Vessel R traversal recorded many separate frames, but there was no single frame saying what R touched during one traverse run.

After this patch, `vessel-r-traverse` records:

```text
RLoopVesselReadPacketFrame
-> RLoopVesselStartHandoffPacketFrame
-> RLoopVesselTraverseResultFrame
-> RLoopVesselActivityLedgerFrame
```

## Code Changes

- Added `songryeon_core/loops/r_loop_vessel_activity_ledger.py`.
- Added `RLoopVesselActivityLedgerFrame`.
- Added `record_r_loop_vessel_activity_ledger(...)`.
- Connected `run_local_r_loop_vessel_traverse(...)` so it records the activity ledger after traversal.
- Added runtime text:

```text
R Vessel activity ledger: status=... / selected=N / inspected=N / candidates=N
```

## What The Ledger Records

The ledger records absolute IDs and counts only:

- source start handoff packet ID
- source read packet ID
- traverse result frame ID
- R1 goal frame ID
- candidate layer surface frame IDs
- R2 surface selection frame IDs
- R2 graph selection frame IDs
- R3 inspection frame IDs
- graph traversal candidate surface frame IDs
- budget frame IDs
- continuation frame IDs
- return summary frame ID
- selected/inspected/candidate graph node IDs
- terminal/raw material counts
- final R task status and failure fields

## Metainfo Boundary

The ledger is absolute information:

- `generated_by=CODE:R_LOOP_VESSEL_ACTIVITY_LEDGER`
- `info_class=absolute`
- `semantic_judgement_status=not_run`

It does not choose important graph nodes, summarize graph memory, reinterpret R3, or write anything to Neo4j.

## Verification

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_195_r_vessel_activity_ledger.py -q
python -m pytest tests/test_order_194_r_vessel_start_handoff.py tests/test_order_195_r_vessel_activity_ledger.py tests/test_order_184_r_vessel_multi_step_traversal.py tests/test_order_176_vessel_r_one_step_traversal.py -q
git diff --check
```

Result:

```text
compileall passed
3 passed
15 passed
git diff --check passed
```

Additional baseline checks:

```powershell
python main.py smoke-test
python -m pytest -q
python -m pytest tests/test_order_146_r_route_experimental_gate.py::test_experimental_r_route_is_not_available_without_gate -q
```

Result:

```text
SMOKE_TEST_OK
full pytest first run: 288 passed, 1 failed due PermissionError writing document_memory_index cache
single rerun of failed test: 1 passed
```

The full pytest failure was not caused by the R Vessel activity ledger code path. The failing test passed when rerun alone after the cache write recovered.

## Remaining Work

ORDER 196 should link this R Vessel activity ledger to the turn capsule / RawCapsule graph path.
