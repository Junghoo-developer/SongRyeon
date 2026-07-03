# ORDER 193 R Result To Node3 Vessel Material Implementation 2026-07-03 001

## Summary

Implemented ORDER 193: R traversal output can now be copied into `Node3InputBriefFrame` as read-only Vessel graph memory material.

This does not enable normal `route=R` live answering by default. It only makes an already recorded Vessel R traversal result visible to node_3 with explicit source/status boundaries.

## Code Changes

- Added `Node3VesselRMaterialItem` and `Node3VesselRMaterial` schema frames.
- Added `vessel_r_material_status`, `vessel_r_material_count`, `vessel_r_material_source_data_ids`, and `vessel_r_material` to `Node3InputBriefFrame`.
- Added a node_2 handoff builder that reads the latest `r_loop:vessel_traverse_result` plus its `r_loop:vessel_read_packet` and copies matching Vessel graph records into node_3 material.
- Added node_3 grounding block/runtime visibility for Vessel R material.
- Added node_3 prompt boundary: Vessel R material is graph memory material, not `read_doc`, `read_code_file`, or normal document context.
- Added node_4 prompt/code guard direction for failed/partial Vessel R material and raw `graph:*` ID exposure.
- Added focused ORDER 193 tests.

## Boundary

- Code copies R traversal status and pre-existing graph summary text.
- Code does not invent semantic relevance.
- Code does not summarize Vessel material.
- Code does not merge R material into L document material.
- R material remains separate from `read_doc`, source-code read, recent memory context, and document context pack.

## Verification

```powershell
python -m compileall songryeon_core main.py tests\test_order_193_r_result_to_node3_vessel_material.py
# passed

python -m pytest tests/test_order_193_r_result_to_node3_vessel_material.py -q
# 3 passed

python main.py smoke-test
# SMOKE_TEST_OK

python -m pytest -q --maxfail=1
# 282 passed in 678.17s

git diff --check
# passed
```

Note: an earlier full `python -m pytest` run hit a 10-minute timeout before output completion. Re-running with a longer limit passed.

## Test Coverage Added

- Successful Vessel R traversal creates node_3 Vessel material.
- Failed Vessel R traversal is preserved as failed with no fake material items.
- node_3 LLM payload receives safe material labels/summary text without raw `graph_node_id`.
- node_4 code guard blocks a final answer that claims Vessel R traversal succeeded when the material says failed.

## Remaining Non-Goals

- No default `route=R`.
- No full R-powered live answer route.
- No Neo4j schema change.
- No new graph write path.
- No raw original read cap increase.
- No R material relevance heuristic.
